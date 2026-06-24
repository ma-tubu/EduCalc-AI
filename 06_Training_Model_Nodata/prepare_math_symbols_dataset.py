from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


CLASS_MAP = {
    "0": "digit_0",
    "1": "digit_1",
    "2": "digit_2",
    "3": "digit_3",
    "4": "digit_4",
    "5": "digit_5",
    "6": "digit_6",
    "7": "digit_7",
    "8": "digit_8",
    "9": "digit_9",
    "add": "op_plus",
    "plus": "op_plus",
    "+": "op_plus",
    "sub": "op_minus",
    "minus": "op_minus",
    "-": "op_minus",
    "mul": "op_mul",
    "times": "op_mul",
    "x": "op_mul",
    "*": "op_mul",
    "div": "op_div",
    "divide": "op_div",
    "/": "op_div",
    "eq": "op_equal",
    "equal": "op_equal",
    "=": "op_equal",
}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def find_class_dirs(source: Path) -> list[tuple[str, Path]]:
    pairs: list[tuple[str, Path]] = []
    for path in source.rglob("*"):
        if not path.is_dir():
            continue
        key = path.name.strip().lower()
        if key in CLASS_MAP:
            pairs.append((key, path))
    return pairs


def foreground_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    arr = np.asarray(image, dtype=np.uint8)
    mask = arr > 20
    if not mask.any():
        return None
    ys, xs = np.where(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def maybe_invert(image: Image.Image, mode: str) -> Image.Image:
    if mode == "no":
        return image
    if mode == "yes":
        return ImageOps.invert(image)

    arr = np.asarray(image, dtype=np.uint8)
    h, w = arr.shape
    corner = np.concatenate(
        [
            arr[: max(1, h // 8), : max(1, w // 8)].ravel(),
            arr[: max(1, h // 8), -max(1, w // 8) :].ravel(),
            arr[-max(1, h // 8) :, : max(1, w // 8)].ravel(),
            arr[-max(1, h // 8) :, -max(1, w // 8) :].ravel(),
        ]
    )
    background_is_light = float(np.median(corner)) > 127.0
    return ImageOps.invert(image) if background_is_light else image


def preprocess_to_28x28(path: Path, invert: str) -> Image.Image:
    image = Image.open(path).convert("L")
    image = ImageOps.autocontrast(image)
    image = maybe_invert(image, invert)

    bbox = foreground_bbox(image)
    if bbox is not None:
        image = image.crop(bbox)

    image = ImageOps.pad(image, (20, 20), method=Image.Resampling.LANCZOS, color=0)
    out = Image.new("L", (28, 28), 0)
    out.paste(image, (4, 4))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert handwritten math-symbol dataset folders into 28x28 grayscale samples."
    )
    parser.add_argument("--source", required=True, help="Dataset root, for example the folder containing 0/add/sub/etc.")
    parser.add_argument("--output", default="data/raw", help="Output folder used by train_15class_keras.py.")
    parser.add_argument("--invert", choices=["auto", "yes", "no"], default="auto")
    parser.add_argument("--clean", action="store_true", help="Remove output class folders before writing.")
    parser.add_argument("--limit-per-class", type=int, default=0, help="0 means no limit.")
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output)
    if not source.exists():
        raise SystemExit(f"Source dataset folder not found: {source}")

    if args.clean and output.exists():
        for folder in set(CLASS_MAP.values()):
            target = output / folder
            if target.exists():
                shutil.rmtree(target)

    for folder in set(CLASS_MAP.values()):
        (output / folder).mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {folder: 0 for folder in set(CLASS_MAP.values())}
    source_dirs = find_class_dirs(source)
    if not source_dirs:
        raise SystemExit(
            "No supported class folders found. Expected names like 0, 1, add, sub, mul, div, eq."
        )

    for class_name, class_dir in source_dirs:
        target_folder = CLASS_MAP[class_name]
        image_paths = [p for p in sorted(class_dir.iterdir()) if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES]
        if args.limit_per_class > 0:
            image_paths = image_paths[: args.limit_per_class]
        for idx, image_path in enumerate(image_paths):
            try:
                image = preprocess_to_28x28(image_path, args.invert)
            except Exception as exc:
                print(f"skip {image_path}: {exc}")
                continue
            out_name = f"{target_folder}_{counts[target_folder]:06d}_{image_path.stem[:24]}.png"
            image.save(output / target_folder / out_name)
            counts[target_folder] += 1

    print(json.dumps(counts, ensure_ascii=False, indent=2))
    print(f"Converted dataset saved to: {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
