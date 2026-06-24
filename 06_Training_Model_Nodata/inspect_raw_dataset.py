from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from train_15class_keras import CLASS_FOLDERS, IGNORED_FOLDERS, LABELS, IMAGE_SUFFIXES, preprocess_image
from train_15class_keras import resolve_user_path


def collect_images(data_dir: Path, include_x_as_mul: bool) -> dict[int, list[Path]]:
    class_folders = {class_id: list(folders) for class_id, folders in CLASS_FOLDERS.items()}
    if include_x_as_mul:
        class_folders[12].append("x")

    result: dict[int, list[Path]] = {}
    known = {name for folders in class_folders.values() for name in folders} | IGNORED_FOLDERS

    for path in sorted(data_dir.iterdir()):
        if path.is_dir() and path.name not in known:
            print(f"Warning: ignored unknown folder: {path.name}")

    for class_id, folders in class_folders.items():
        paths: list[Path] = []
        for folder in folders:
            folder_path = data_dir / folder
            if folder_path.exists():
                paths.extend(
                    p for p in sorted(folder_path.iterdir()) if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
                )
        result[class_id] = paths
    return result


def save_preview(samples: dict[int, list[Path]], output: Path, per_class: int) -> None:
    cell = 56
    label_h = 16
    width = per_class * cell
    height = len(LABELS) * (cell + label_h)
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)

    for class_id, label in enumerate(LABELS):
        y = class_id * (cell + label_h)
        draw.text((2, y), f"{label} ({len(samples[class_id])})", fill=(0, 0, 0))
        shown = 0
        for col, path in enumerate(samples[class_id][:per_class]):
            try:
                arr = preprocess_image(path)
            except Exception as exc:
                print(f"Warning: skipped unreadable preview image: {path} ({exc})")
                continue
            image = Image.fromarray((arr * 255).astype("uint8"), mode="L").resize((48, 48))
            sheet.paste(Image.merge("RGB", (image, image, image)), (shown * cell + 4, y + label_h))
            shown += 1
            if shown >= per_class:
                break

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect raw handwritten math-symbol dataset.")
    parser.add_argument("--data-dir", default="data/raw")
    parser.add_argument("--preview", default="reports/preprocess_preview.png")
    parser.add_argument("--per-class", type=int, default=8)
    parser.add_argument("--include-x-as-mul", action="store_true")
    args = parser.parse_args()

    data_dir = resolve_user_path(args.data_dir)
    print(f"Using data_dir: {data_dir.resolve()}")
    samples = collect_images(data_dir, args.include_x_as_mul)
    print("Sample count by class:")
    for class_id, label in enumerate(LABELS):
        print(f"  {label}: {len(samples[class_id])}")

    preview_path = resolve_user_path(args.preview)
    save_preview(samples, preview_path, args.per_class)
    print(f"Preview saved to: {preview_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
