#!/usr/bin/env python3
"""Build a line-image UART payload from prepared 28x28 samples."""

from __future__ import annotations

import argparse
from pathlib import Path

PAYLOAD_NAMES = {
    "0": "payload_0_784.txt",
    "1": "payload_1_784.txt",
    "2": "payload_2_784.txt",
    "3": "payload_3_784.txt",
    "4": "payload_4_784.txt",
    "5": "payload_5_784.txt",
    "6": "payload_6_784.txt",
    "7": "payload_7_784.txt",
    "8": "payload_8_784.txt",
    "9": "payload_9_784.txt",
    "+": "payload_plus_784.txt",
    "-": "payload_minus_784.txt",
    "*": "payload_mul_784.txt",
    "x": "payload_mul_784.txt",
    "X": "payload_mul_784.txt",
    "/": "payload_div_784.txt",
    "=": "payload_eq_784.txt",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Concatenate cropped symbols into a single HxW UART payload."
    )
    parser.add_argument("--expr", required=True, help="Expression, e.g. 3+2=5 or 9*9=81")
    parser.add_argument(
        "--payload-dir",
        default=Path("reports") / "uart_payloads",
        type=Path,
        help="Directory containing payload_*_784.txt files.",
    )
    parser.add_argument("--gap", type=int, default=2, help="Blank columns between symbols.")
    parser.add_argument("--no-crop", action="store_true", help="Keep every symbol as a full 28-column block.")
    parser.add_argument("--height", type=int, default=28, help="Output image height.")
    parser.add_argument(
        "--header",
        action="store_true",
        help="Prefix payload with '-1 width height' for arbitrary HxW board input.",
    )
    parser.add_argument("--threshold", type=int, default=30, help="Ink threshold in 0..255.")
    parser.add_argument("--output", type=Path, help="Output txt path.")
    parser.add_argument("--preview", type=Path, help="Optional preview PGM path.")
    return parser.parse_args()


def read_symbol(path: Path) -> list[list[int]]:
    nums = [int(float(x)) for x in path.read_text(encoding="ascii").split()]
    if len(nums) != 784:
        raise SystemExit(f"{path} has {len(nums)} numbers, expected 784")
    return [nums[y * 28 : (y + 1) * 28] for y in range(28)]


def crop_cols(img: list[list[int]], threshold: int) -> list[list[int]]:
    used_cols = [
        x for x in range(28)
        if any(img[y][x] > threshold for y in range(28))
    ]
    if not used_cols:
        return [[0] for _ in range(28)]
    x0, x1 = min(used_cols), max(used_cols)
    return [row[x0 : x1 + 1] for row in img]


def safe_name(expr: str) -> str:
    return (
        expr.replace("+", "plus")
        .replace("-", "minus")
        .replace("*", "mul")
        .replace("/", "div")
        .replace("=", "eq")
    )


def main() -> int:
    args = parse_args()
    expr = args.expr.strip().replace(" ", "")
    if not (1 <= len(expr) <= 7):
        raise SystemExit("Expression length must be 1..7 characters.")

    rows28 = [[] for _ in range(28)]
    payload_dir = args.payload_dir
    for idx, ch in enumerate(expr):
        if ch not in PAYLOAD_NAMES:
            raise SystemExit(f"Unsupported character: {ch!r}")
        full_symbol = read_symbol(payload_dir / PAYLOAD_NAMES[ch])
        symbol = full_symbol if args.no_crop else crop_cols(full_symbol, args.threshold)
        for y in range(28):
            rows28[y].extend(symbol[y])
            if idx != len(expr) - 1:
                rows28[y].extend([0] * args.gap)

    if args.height < 28:
        raise SystemExit("--height must be at least 28")
    if (args.height != 28) and (not args.header):
        raise SystemExit("Non-28 height needs --header so the board knows width and height.")

    top = (args.height - 28) // 2
    bottom = args.height - 28 - top
    width = len(rows28[0])
    rows = [[0] * width for _ in range(top)] + rows28 + [[0] * width for _ in range(bottom)]

    flat_values = [v for row in rows for v in row]
    if args.header:
        flat = ["-1", str(width), str(args.height)] + [str(v) for v in flat_values]
    else:
        flat = [str(v) for v in flat_values]

    prefix = "payload_header" if args.header else "payload_line28"
    output = args.output or (payload_dir / f"{prefix}_{safe_name(expr)}_{args.height}x{width}.txt")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(" ".join(flat), encoding="ascii")

    if args.preview:
        preview = args.preview
        if preview.suffix.lower() != ".pgm":
            preview = preview.with_suffix(".pgm")
        preview.parent.mkdir(parents=True, exist_ok=True)
        data = bytes(int(v) for row in rows for v in row)
        preview.write_bytes(f"P5\n{width} {args.height}\n255\n".encode("ascii") + data)
        print(f"Preview: {preview}")

    print(f"Wrote {output}")
    print(f"Shape: {args.height}x{width}")
    print(f"Numbers: {len(flat)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
