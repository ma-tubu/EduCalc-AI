import argparse
import sys
import time
from pathlib import Path

from PIL import Image, ImageOps
import serial
from serial.tools import list_ports


def block_average_28x28(image: Image.Image) -> Image.Image:
    width, height = image.size
    block_size = 28
    new_width = (width // block_size) * block_size
    new_height = (height // block_size) * block_size
    if new_width == 0 or new_height == 0:
        raise ValueError("Image must be at least 28x28 pixels for MATLAB block-average mode.")

    cropped = image.crop((0, 0, new_width, new_height))
    pixels = cropped.load()
    tile_width = new_width // block_size
    tile_height = new_height // block_size
    out_pixels = []

    for y in range(block_size):
        for x in range(block_size):
            total = 0
            count = tile_width * tile_height
            for yy in range(y * tile_height, (y + 1) * tile_height):
                for xx in range(x * tile_width, (x + 1) * tile_width):
                    total += pixels[xx, yy]
            out_pixels.append(int(total / count + 0.5))

    output = Image.new("L", (block_size, block_size))
    output.putdata(out_pixels)
    return output


def load_digit_image(path: Path, invert: str, fit: str, autocontrast: bool) -> Image.Image:
    image = Image.open(path).convert("L")

    if autocontrast:
        image = ImageOps.autocontrast(image)

    if fit == "blockavg":
        canvas = block_average_28x28(image)
    elif fit == "stretch":
        canvas = image.resize((28, 28), Image.Resampling.BILINEAR)
    else:
        image = ImageOps.contain(image, (28, 28), Image.Resampling.BILINEAR)
        canvas = Image.new("L", (28, 28), color=0)
        x = (28 - image.width) // 2
        y = (28 - image.height) // 2
        canvas.paste(image, (x, y))

    if invert == "yes":
        canvas = ImageOps.invert(canvas)
    elif invert == "auto":
        pixels = list(canvas.getdata())
        mean_value = sum(pixels) / len(pixels)
        if mean_value > 127:
            canvas = ImageOps.invert(canvas)

    return canvas


def image_to_ascii_payload(image: Image.Image) -> bytes:
    pixels = list(image.getdata())
    text = " ".join(str(int(v)) for v in pixels)
    return text.encode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send one 28x28 grayscale digit image to the STM32F7 baseline project."
    )
    parser.add_argument("--port", help="Serial port, for example COM3. Required unless --print-only or --list-ports is used.")
    parser.add_argument("--image", help="Path to digit image. Required unless --list-ports is used.")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate. Baseline firmware uses 9600.")
    parser.add_argument(
        "--invert",
        choices=["auto", "yes", "no"],
        default="auto",
        help="Invert image so the model receives MNIST-like black background and bright strokes.",
    )
    parser.add_argument(
        "--fit",
        choices=["blockavg", "stretch", "contain"],
        default="blockavg",
        help="Resize mode. 'blockavg' matches the reference MATLAB preprocessing; 'stretch' uses bilinear resize; 'contain' preserves aspect ratio with padding.",
    )
    parser.add_argument(
        "--autocontrast",
        action="store_true",
        help="Apply grayscale autocontrast before resizing. Leave off to preserve original grayscale values.",
    )
    parser.add_argument("--preview", help="Optional path to save the generated 28x28 preview PNG.")
    parser.add_argument("--read-seconds", type=float, default=5.0, help="Seconds to read board output after send.")
    parser.add_argument("--list-ports", action="store_true", help="List available serial ports and exit.")
    parser.add_argument("--append-newline", action="store_true", help="Append CRLF after the ASCII payload.")
    parser.add_argument("--chunk-size", type=int, default=0, help="Send payload in chunks. 0 means send all at once.")
    parser.add_argument("--chunk-delay", type=float, default=0.02, help="Delay between chunks in seconds.")
    parser.add_argument("--print-only", action="store_true", help="Print the 784-value payload instead of opening serial port.")
    parser.add_argument("--output-txt", help="Optional text file path to save the 784-value payload.")
    args = parser.parse_args()

    if args.list_ports:
        ports = list(list_ports.comports())
        if not ports:
            print("No serial ports found.")
            return 1
        for port in ports:
            print(f"{port.device}: {port.description}")
        return 0

    if not args.image:
        print("--image is required unless --list-ports is used.", file=sys.stderr)
        return 2

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Image not found: {image_path}", file=sys.stderr)
        return 2

    image = load_digit_image(image_path, args.invert, args.fit, args.autocontrast)
    if args.preview:
        image.save(args.preview)

    payload = image_to_ascii_payload(image)
    if args.append_newline:
        payload += b"\r\n"
    token_count = len(image.getdata())
    print(f"Prepared {token_count} pixels. First 12 pixels: {list(image.getdata())[:12]}")
    if args.output_txt:
        Path(args.output_txt).write_bytes(payload)
        print(f"Saved payload to {args.output_txt}")
    if args.print_only:
        print(payload.decode("ascii"))
        return 0

    if not args.port:
        print("--port is required unless --print-only or --list-ports is used.", file=sys.stderr)
        return 2

    print(f"Sending {len(payload)} bytes to {args.port} at {args.baud} baud.")

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.2)
    except serial.SerialException as exc:
        print(f"Could not open serial port {args.port}: {exc}", file=sys.stderr)
        print("Available ports:", file=sys.stderr)
        for port in list_ports.comports():
            print(f"  {port.device}: {port.description}", file=sys.stderr)
        print("Close XCOM/other serial tools before running this script.", file=sys.stderr)
        return 3

    with ser:
        time.sleep(0.5)
        ser.reset_input_buffer()
        if args.chunk_size and args.chunk_size > 0:
            for start in range(0, len(payload), args.chunk_size):
                ser.write(payload[start : start + args.chunk_size])
                ser.flush()
                time.sleep(args.chunk_delay)
        else:
            ser.write(payload)
        ser.flush()
        time.sleep(0.2)

        deadline = time.time() + args.read_seconds
        received = bytearray()
        while time.time() < deadline:
            chunk = ser.read(256)
            if chunk:
                received.extend(chunk)

    if received:
        print(received.decode(errors="replace"))
    else:
        print("No response received. Check COM port, baud rate, wiring, and firmware state.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
