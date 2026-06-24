#!/usr/bin/env python3
"""Build a 1-7 character UART payload from prepared 784-number samples."""

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
        description="Concatenate 1-7 28x28 UART payloads into one 784*N-number frame."
    )
    parser.add_argument("--expr", required=True, help="Expression with 1-7 chars, e.g. 3+2=5")
    parser.add_argument(
        "--payload-dir",
        default=Path("reports") / "uart_payloads",
        type=Path,
        help="Directory containing payload_*_784.txt files.",
    )
    parser.add_argument("--output", type=Path, help="Output txt path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    expr = args.expr.strip().replace(" ", "")
    if not (1 <= len(expr) <= 7):
        raise SystemExit("Expression length must be 1..7 characters.")

    payload_dir = args.payload_dir
    parts: list[str] = []
    for ch in expr:
        if ch not in PAYLOAD_NAMES:
            raise SystemExit(f"Unsupported character: {ch!r}")
        payload_path = payload_dir / PAYLOAD_NAMES[ch]
        if not payload_path.exists():
            raise SystemExit(f"Missing payload file: {payload_path}")
        nums = payload_path.read_text(encoding="ascii").split()
        if len(nums) != 784:
            raise SystemExit(f"{payload_path} has {len(nums)} numbers, expected 784")
        parts.extend(nums)

    expected_count = len(expr) * 784
    if len(parts) != expected_count:
        raise SystemExit(f"Internal error: got {len(parts)} numbers")

    output = args.output
    if output is None:
        safe = (
            expr.replace("+", "plus")
            .replace("-", "minus")
            .replace("*", "mul")
            .replace("/", "div")
            .replace("=", "eq")
        )
        output = payload_dir / f"payload_expr_{safe}_{expected_count}.txt"

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(" ".join(parts), encoding="ascii")
    print(f"Wrote {output}")
    print(f"Numbers: {expected_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
