from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from train_15class_keras import CLASS_FOLDERS, IMAGE_SUFFIXES, LABELS, preprocess_image, resolve_user_path


ALIASES = {
    "plus": "+",
    "add": "+",
    "minus": "-",
    "sub": "-",
    "mul": "*",
    "times": "*",
    "div": "/",
    "eq": "=",
    "equal": "=",
}


def normalize_label(label: str) -> str:
    return ALIASES.get(label, label)


def class_id_from_label(label: str) -> int:
    label = normalize_label(label)
    if label not in LABELS:
        raise SystemExit(f"Unsupported label {label!r}. Use one of: {LABELS}")
    return LABELS.index(label)


def find_images(data_dir: Path, class_id: int, include_x_as_mul: bool) -> list[Path]:
    folders = list(CLASS_FOLDERS[class_id])
    if include_x_as_mul and LABELS[class_id] == "*":
        folders.append("x")

    images: list[Path] = []
    for folder in folders:
        folder_path = data_dir / folder
        if folder_path.exists():
            images.extend(
                path
                for path in sorted(folder_path.iterdir())
                if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
            )
    return images


def write_payload(image_path: Path, output_txt: Path, preview: Path | None) -> None:
    arr = preprocess_image(image_path)
    pixels = (arr * 255.0).round().clip(0, 255).astype("uint8")
    payload = " ".join(str(int(v)) for v in pixels.reshape(-1))
    output_txt.parent.mkdir(parents=True, exist_ok=True)
    output_txt.write_text(payload, encoding="ascii")

    if preview is not None:
        preview.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(pixels, mode="L").save(preview)

    print(f"Source image: {image_path}")
    print(f"Payload numbers: {pixels.size}")
    print(f"First 16 pixels: {pixels.reshape(-1)[:16].tolist()}")
    print(f"Payload saved to: {output_txt.resolve()}")
    if preview is not None:
        print(f"Preview saved to: {preview.resolve()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a 784-number UART payload from a dataset sample.")
    parser.add_argument("--data-dir", default="data/raw")
    parser.add_argument("--label", default="+", help="Label to pick, such as 8, plus, minus, mul, div, eq.")
    parser.add_argument("--index", type=int, default=0, help="Sample index inside the selected class.")
    parser.add_argument("--image", help="Use an explicit image path instead of --label/--index.")
    parser.add_argument("--output-txt", default="reports/dataset_payload_784.txt")
    parser.add_argument("--preview", default="reports/dataset_payload_preview.png")
    parser.add_argument("--include-x-as-mul", action="store_true")
    args = parser.parse_args()

    if args.image:
        image_path = resolve_user_path(args.image)
    else:
        data_dir = resolve_user_path(args.data_dir)
        class_id = class_id_from_label(args.label)
        images = find_images(data_dir, class_id, args.include_x_as_mul)
        if not images:
            raise SystemExit(f"No images found for label {LABELS[class_id]!r} in {data_dir}")
        if args.index < 0 or args.index >= len(images):
            raise SystemExit(f"--index out of range: {args.index}; valid range is 0..{len(images) - 1}")
        image_path = images[args.index]

    preview = resolve_user_path(args.preview) if args.preview else None
    write_payload(image_path, resolve_user_path(args.output_txt), preview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
