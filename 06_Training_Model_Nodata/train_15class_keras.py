from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
import tensorflow as tf


SCRIPT_DIR = Path(__file__).resolve().parent
LABELS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "+", "-", "*", "/", "="]
CLASS_FOLDERS = {
    0: ["digit_0", "0"],
    1: ["digit_1", "1"],
    2: ["digit_2", "2"],
    3: ["digit_3", "3"],
    4: ["digit_4", "4"],
    5: ["digit_5", "5"],
    6: ["digit_6", "6"],
    7: ["digit_7", "7"],
    8: ["digit_8", "8"],
    9: ["digit_9", "9"],
    10: ["op_plus", "add", "plus", "+"],
    11: ["op_minus", "sub", "minus", "-"],
    12: ["op_mul", "mul", "times", "*"],
    13: ["op_div", "div", "divide", "/"],
    14: ["op_equal", "eq", "equal", "="],
}
IGNORED_FOLDERS = {"dec", "x", "y", "z"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def resolve_user_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return SCRIPT_DIR / path


def preprocess_image(path: Path) -> np.ndarray:
    image = Image.open(path).convert("L")
    image = ImageOps.autocontrast(image)

    arr = np.asarray(image, dtype=np.uint8)
    if arr.mean() > 127:
        image = ImageOps.invert(image)

    bbox = image.getbbox()
    if bbox is not None:
        image = image.crop(bbox)

    image = ImageOps.pad(image, (20, 20), method=Image.Resampling.LANCZOS, color=0)
    out = Image.new("L", (28, 28), 0)
    out.paste(image, (4, 4))
    return np.asarray(out, dtype=np.float32) / 255.0


def load_local_samples(data_dir: Path, include_x_as_mul: bool) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    xs: list[np.ndarray] = []
    ys: list[int] = []
    counts = {label: 0 for label in LABELS}
    skipped = 0

    class_folders = {class_id: list(folders) for class_id, folders in CLASS_FOLDERS.items()}
    if include_x_as_mul:
        class_folders[12].append("x")

    known_folder_names = {name for folders in class_folders.values() for name in folders} | IGNORED_FOLDERS
    unknown_dirs = [
        path.name
        for path in sorted(data_dir.iterdir())
        if path.is_dir() and path.name not in known_folder_names
    ]
    if unknown_dirs:
        print(f"Warning: ignored unknown class folders: {unknown_dirs}")

    for class_id, folders in class_folders.items():
        for folder in folders:
            folder_path = data_dir / folder
            if not folder_path.exists():
                continue
            for path in sorted(folder_path.glob("*")):
                if path.suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                try:
                    xs.append(preprocess_image(path))
                except (UnidentifiedImageError, OSError, ValueError) as exc:
                    skipped += 1
                    print(f"Warning: skipped unreadable image: {path} ({exc})")
                    continue
                ys.append(class_id)
                counts[LABELS[class_id]] += 1

    if skipped:
        print(f"Warning: skipped {skipped} unreadable image(s).")

    if not xs:
        return np.empty((0, 28, 28), dtype=np.float32), np.empty((0,), dtype=np.int64), counts
    return np.stack(xs).astype(np.float32), np.asarray(ys, dtype=np.int64), counts


def load_dataset(
    data_dir: Path,
    include_mnist: bool,
    max_mnist_per_digit: int | None,
    include_x_as_mul: bool,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    local_x, local_y, counts = load_local_samples(data_dir, include_x_as_mul)
    symbol_count = int(np.sum(local_y >= 10))
    if symbol_count == 0:
        raise SystemExit(
            "No operator samples found. Expected folders such as add, sub, mul, div, eq "
            "or op_plus, op_minus, op_mul, op_div, op_equal."
        )
    missing = [LABELS[i] for i in range(len(LABELS)) if counts[LABELS[i]] == 0]
    if missing:
        raise SystemExit(f"Missing required classes in {data_dir}: {missing}")

    x_parts = [local_x]
    y_parts = [local_y]

    if include_mnist:
        (mnist_x, mnist_y), _ = tf.keras.datasets.mnist.load_data()
        mnist_x = mnist_x.astype(np.float32) / 255.0

        if max_mnist_per_digit:
            picked_x = []
            picked_y = []
            for digit in range(10):
                idx = np.where(mnist_y == digit)[0][:max_mnist_per_digit]
                picked_x.append(mnist_x[idx])
                picked_y.append(mnist_y[idx])
            mnist_x = np.concatenate(picked_x, axis=0)
            mnist_y = np.concatenate(picked_y, axis=0)

        x_parts.append(mnist_x)
        y_parts.append(mnist_y.astype(np.int64))
        for digit in range(10):
            counts[LABELS[digit]] += int(np.sum(mnist_y == digit))

    x = np.concatenate(x_parts, axis=0)
    y = np.concatenate(y_parts, axis=0)
    x = x[..., np.newaxis]
    return x, y, counts


def build_model() -> tf.keras.Model:
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(28, 28, 1), name="image"),
            tf.keras.layers.Conv2D(8, 3, activation="relu", padding="same"),
            tf.keras.layers.MaxPooling2D(2),
            tf.keras.layers.Conv2D(16, 3, activation="relu", padding="same"),
            tf.keras.layers.MaxPooling2D(2),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dense(len(LABELS), activation="softmax", name="prob"),
        ]
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def export_tflite(model: tf.keras.Model, out_path: Path) -> None:
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    out_path.write_bytes(tflite_model)


def export_int8_tflite(model: tf.keras.Model, out_path: Path, representative_x: np.ndarray) -> None:
    def representative_dataset():
        for sample in representative_x[:200].astype(np.float32):
            yield [sample[np.newaxis, ...]]

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    out_path.write_bytes(converter.convert())


def write_confusion_matrix(path: Path, y_true: np.ndarray, y_pred: np.ndarray) -> None:
    matrix = confusion_matrix(y_true, y_pred, labels=list(range(len(LABELS))))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["true\\pred", *LABELS])
        for label, row in zip(LABELS, matrix):
            writer.writerow([label, *row.tolist()])


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a 15-class handwritten arithmetic character model.")
    parser.add_argument("--data-dir", default="data/raw")
    parser.add_argument("--exports-dir", default="exports")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--include-mnist", action="store_true", help="Also add MNIST digit samples.")
    parser.add_argument("--max-mnist-per-digit", type=int, default=3000)
    parser.add_argument("--include-x-as-mul", action="store_true", help="Treat folder 'x' as multiplication samples.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    tf.keras.utils.set_random_seed(args.seed)
    data_dir = resolve_user_path(args.data_dir)
    exports_dir = resolve_user_path(args.exports_dir)
    reports_dir = resolve_user_path(args.reports_dir)
    exports_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    print(f"Using data_dir: {data_dir.resolve()}")

    x, y, counts = load_dataset(
        data_dir,
        include_mnist=args.include_mnist,
        max_mnist_per_digit=args.max_mnist_per_digit,
        include_x_as_mul=args.include_x_as_mul,
    )
    print("Sample count by class:")
    for label in LABELS:
        print(f"  {label}: {counts[label]}")

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.18, random_state=args.seed, stratify=y
    )

    model = build_model()
    model.summary()
    history = model.fit(
        x_train,
        y_train,
        validation_data=(x_test, y_test),
        epochs=args.epochs,
        batch_size=args.batch_size,
        shuffle=True,
    )

    loss, acc = model.evaluate(x_test, y_test, verbose=0)
    probs = model.predict(x_test, batch_size=args.batch_size, verbose=0)
    y_pred = np.argmax(probs, axis=1)

    model.save(exports_dir / "hand_expr_15class.keras")
    model.save(exports_dir / "hand_expr_15class.h5")
    export_tflite(model, exports_dir / "hand_expr_15class.tflite")
    export_int8_tflite(model, exports_dir / "hand_expr_15class_int8.tflite", x_train)
    (exports_dir / "labels_15class.txt").write_text("\n".join(LABELS) + "\n", encoding="utf-8")

    write_confusion_matrix(reports_dir / "confusion_matrix.csv", y_test, y_pred)
    report = {
        "labels": LABELS,
        "sample_count": counts,
        "test_loss": float(loss),
        "test_accuracy": float(acc),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "history": {k: [float(vv) for vv in v] for k, v in history.history.items()},
    }
    (reports_dir / "training_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Test accuracy: {acc:.4f}")
    print(f"Saved exports to: {exports_dir.resolve()}")
    print(f"Saved reports to: {reports_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
