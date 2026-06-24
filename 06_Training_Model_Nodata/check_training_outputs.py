from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


EXPECTED_EXPORTS = [
    "hand_expr_15class.keras",
    "hand_expr_15class.h5",
    "hand_expr_15class.tflite",
    "hand_expr_15class_int8.tflite",
    "labels_15class.txt",
]


def format_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.2f} MB"
    return f"{size / 1024:.1f} KB"


def print_exports(exports_dir: Path) -> bool:
    print("Export files:")
    ok = True
    for name in EXPECTED_EXPORTS:
        path = exports_dir / name
        if path.exists():
            print(f"  OK   {name:32s} {format_size(path.stat().st_size)}")
        else:
            ok = False
            print(f"  MISS {name}")
    return ok


def print_report(reports_dir: Path) -> None:
    report_path = reports_dir / "training_report.json"
    if not report_path.exists():
        print("No training_report.json found yet.")
        return

    report = json.loads(report_path.read_text(encoding="utf-8"))
    print("\nTraining report:")
    print(f"  test_accuracy: {report.get('test_accuracy', 0):.4f}")
    print(f"  test_loss:     {report.get('test_loss', 0):.4f}")
    print("  sample_count:")
    for label, count in report.get("sample_count", {}).items():
        print(f"    {label:>2s}: {count}")


def print_confusion_hint(reports_dir: Path) -> None:
    matrix_path = reports_dir / "confusion_matrix.csv"
    if not matrix_path.exists():
        print("\nNo confusion_matrix.csv found yet.")
        return

    with matrix_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    labels = rows[0][1:]
    print("\nPer-class validation accuracy from confusion matrix:")
    for row in rows[1:]:
        label = row[0]
        values = [int(v) for v in row[1:]]
        total = sum(values)
        correct = values[labels.index(label)] if label in labels else 0
        acc = correct / total if total else 0
        flag = "CHECK" if acc < 0.90 else "OK"
        print(f"  {label:>2s}: {acc:.3f} ({correct}/{total}) {flag}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 15-class training outputs before Cube.AI import.")
    parser.add_argument("--exports-dir", default="exports")
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args()

    exports_ok = print_exports(Path(args.exports_dir))
    print_report(Path(args.reports_dir))
    print_confusion_hint(Path(args.reports_dir))

    if not exports_ok:
        print("\nTraining or export has not finished yet.")
        return 1
    print("\nNext: import exports/hand_expr_15class.tflite into STM32Cube.AI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
