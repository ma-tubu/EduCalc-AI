from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageDraw, ImageOps


LABELS = [
    ("+", "op_plus"),
    ("-", "op_minus"),
    ("*", "op_mul"),
    ("/", "op_div"),
    ("=", "op_equal"),
]


class SampleCollector:
    def __init__(self, root: tk.Tk, out_dir: Path, canvas_size: int = 280) -> None:
        self.root = root
        self.out_dir = out_dir
        self.canvas_size = canvas_size
        self.current_label = tk.StringVar(value=LABELS[0][0])
        self.brush_size = tk.IntVar(value=14)
        self.last_xy: tuple[int, int] | None = None

        self.image = Image.new("L", (canvas_size, canvas_size), 0)
        self.draw = ImageDraw.Draw(self.image)

        root.title("15-class symbol sample collector")
        root.resizable(False, False)

        bar = ttk.Frame(root, padding=8)
        bar.grid(row=0, column=0, sticky="ew")

        ttk.Label(bar, text="Label").grid(row=0, column=0, padx=(0, 4))
        ttk.Combobox(
            bar,
            textvariable=self.current_label,
            values=[label for label, _ in LABELS],
            width=5,
            state="readonly",
        ).grid(row=0, column=1, padx=(0, 10))

        ttk.Label(bar, text="Brush").grid(row=0, column=2, padx=(0, 4))
        ttk.Scale(bar, from_=6, to=28, variable=self.brush_size, orient="horizontal", length=120).grid(
            row=0, column=3, padx=(0, 10)
        )

        ttk.Button(bar, text="Save  S", command=self.save_sample).grid(row=0, column=4, padx=4)
        ttk.Button(bar, text="Clear  C", command=self.clear).grid(row=0, column=5, padx=4)

        self.status = ttk.Label(root, text="Draw with mouse. Press S to save, C to clear.")
        self.status.grid(row=2, column=0, sticky="w", padx=8, pady=(0, 8))

        self.canvas = tk.Canvas(root, width=canvas_size, height=canvas_size, bg="black", cursor="crosshair")
        self.canvas.grid(row=1, column=0, padx=8, pady=8)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        root.bind("s", lambda _event: self.save_sample())
        root.bind("S", lambda _event: self.save_sample())
        root.bind("c", lambda _event: self.clear())
        root.bind("C", lambda _event: self.clear())

        for _, folder in LABELS:
            (self.out_dir / folder).mkdir(parents=True, exist_ok=True)

    def on_press(self, event: tk.Event) -> None:
        self.last_xy = (event.x, event.y)
        self.paint(event.x, event.y, event.x, event.y)

    def on_drag(self, event: tk.Event) -> None:
        if self.last_xy is None:
            self.last_xy = (event.x, event.y)
        x0, y0 = self.last_xy
        self.paint(x0, y0, event.x, event.y)
        self.last_xy = (event.x, event.y)

    def on_release(self, _event: tk.Event) -> None:
        self.last_xy = None

    def paint(self, x0: int, y0: int, x1: int, y1: int) -> None:
        width = int(self.brush_size.get())
        self.canvas.create_line(x0, y0, x1, y1, fill="white", width=width, capstyle=tk.ROUND, smooth=True)
        self.draw.line((x0, y0, x1, y1), fill=255, width=width)

    def clear(self) -> None:
        self.canvas.delete("all")
        self.image = Image.new("L", (self.canvas_size, self.canvas_size), 0)
        self.draw = ImageDraw.Draw(self.image)
        self.status.config(text="Cleared.")

    def save_sample(self) -> None:
        label = self.current_label.get()
        folder = dict(LABELS)[label]
        processed = preprocess_to_28x28(self.image)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self.out_dir / folder / f"{folder}_{stamp}.png"
        processed.save(path)
        self.status.config(text=f"Saved {label}: {path.name}")
        self.clear()


def preprocess_to_28x28(image: Image.Image) -> Image.Image:
    image = image.convert("L")
    bbox = image.getbbox()
    if bbox is None:
        return Image.new("L", (28, 28), 0)

    digit = image.crop(bbox)
    digit = ImageOps.pad(digit, (20, 20), method=Image.Resampling.LANCZOS, color=0)
    out = Image.new("L", (28, 28), 0)
    out.paste(digit, (4, 4))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect operator samples for the 15-class handwritten model.")
    parser.add_argument("--out-dir", default="data/raw", help="Output dataset root.")
    args = parser.parse_args()

    root = tk.Tk()
    SampleCollector(root, Path(args.out_dir))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
