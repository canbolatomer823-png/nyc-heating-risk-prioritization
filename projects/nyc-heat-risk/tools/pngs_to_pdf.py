from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image
from reportlab.pdfgen import canvas


def main() -> None:
    if len(sys.argv) < 4:
        raise SystemExit("Usage: pngs_to_pdf.py <png_dir> <glob> <output.pdf>")

    png_dir = Path(sys.argv[1])
    pattern = sys.argv[2]
    output_pdf = Path(sys.argv[3])
    images = sorted(png_dir.glob(pattern))
    if not images:
        raise SystemExit(f"No PNG files matched {png_dir}/{pattern}")

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_pdf))
    for image_path in images:
        with Image.open(image_path) as img:
            width, height = img.size
        c.setPageSize((width, height))
        c.drawImage(str(image_path), 0, 0, width=width, height=height)
        c.showPage()
    c.save()
    print(output_pdf)
    print(f"pages={len(images)}")


if __name__ == "__main__":
    main()
