#!/usr/bin/env python3
"""Safely extract the tutorial image ZIP and build a review contact sheet."""
from __future__ import annotations

import csv
import math
import shutil
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE = Path(__file__).resolve().parent
ARCHIVE = BASE / "input" / "final_24MB.zip"
OUT = BASE / "prepared-input"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
MAX_FILES = 5000
MAX_UNCOMPRESSED = 500 * 1024 * 1024
THUMB_W, THUMB_H = 240, 180
CELL_W, CELL_H = 260, 220
COLUMNS = 4


def safe_member(name: str) -> bool:
    p = PurePosixPath(name)
    return not p.is_absolute() and ".." not in p.parts and not name.startswith(("/", "\\"))


def main() -> None:
    if not ARCHIVE.is_file():
        raise SystemExit(f"ZIP not found: {ARCHIVE}")
    if OUT.exists():
        shutil.rmtree(OUT)
    images_dir = OUT / "images"
    images_dir.mkdir(parents=True)

    records = []
    with zipfile.ZipFile(ARCHIVE) as zf:
        members = [i for i in zf.infolist() if not i.is_dir()]
        if len(members) > MAX_FILES:
            raise SystemExit(f"Archive contains too many files ({len(members)} > {MAX_FILES}).")
        total_size = sum(i.file_size for i in members)
        if total_size > MAX_UNCOMPRESSED:
            raise SystemExit(f"Archive expands beyond the {MAX_UNCOMPRESSED // (1024*1024)} MB safety limit.")
        candidates = []
        for info in members:
            if not safe_member(info.filename):
                print(f"Skipping unsafe archive path: {info.filename}")
                continue
            path = PurePosixPath(info.filename)
            if path.suffix.lower() not in IMAGE_EXTS or path.name.startswith("._") or "__MACOSX" in path.parts:
                continue
            candidates.append(info)

        candidates.sort(key=lambda x: (PurePosixPath(x.filename).name.casefold(), x.filename.casefold()))
        if not candidates:
            raise SystemExit("No supported image files were found in the ZIP.")

        for index, info in enumerate(candidates, start=1):
            target = images_dir / f"image-{index:03d}{PurePosixPath(info.filename).suffix.lower()}"
            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            try:
                with Image.open(target) as im:
                    width, height = im.size
                    fmt = im.format or ""
                    im.verify()
                records.append({
                    "order": index,
                    "original_name": info.filename,
                    "extracted_name": target.name,
                    "width": width,
                    "height": height,
                    "format": fmt,
                    "bytes": info.file_size,
                    "status": "ok",
                })
            except Exception as exc:
                target.unlink(missing_ok=True)
                records.append({
                    "order": index,
                    "original_name": info.filename,
                    "extracted_name": "",
                    "width": "",
                    "height": "",
                    "format": "",
                    "bytes": info.file_size,
                    "status": f"unreadable: {type(exc).__name__}",
                })

    with (OUT / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["order", "original_name", "extracted_name", "width", "height", "format", "bytes", "status"])
        writer.writeheader()
        writer.writerows(records)

    good = [r for r in records if r["status"] == "ok"]
    if not good:
        raise SystemExit("Image files were found, but none could be opened.")
    rows = math.ceil(len(good) / COLUMNS)
    sheet = Image.new("RGB", (COLUMNS * CELL_W, rows * CELL_H), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 13)
    except OSError:
        font = ImageFont.load_default()

    for pos, record in enumerate(good):
        image_path = images_dir / record["extracted_name"]
        with Image.open(image_path) as im:
            thumb = ImageOps.contain(im.convert("RGB"), (THUMB_W, THUMB_H))
        x = (pos % COLUMNS) * CELL_W
        y = (pos // COLUMNS) * CELL_H
        px = x + (THUMB_W - thumb.width) // 2 + 10
        py = y + 5 + (THUMB_H - thumb.height) // 2
        sheet.paste(thumb, (px, py))
        draw.text((x + 10, y + THUMB_H + 12), f'{record["order"]:03d}  {record["original_name"][:30]}', fill="black", font=font)
        draw.text((x + 10, y + THUMB_H + 32), f'{record["width"]} x {record["height"]}', fill="gray", font=font)

    sheet.save(OUT / "contact-sheet.jpg", quality=88)
    (OUT / "SUMMARY.txt").write_text(
        f"Images successfully extracted: {len(good)}\n"
        f"Image files detected: {len(records)}\n"
        f"Unreadable images: {len(records) - len(good)}\n"
        "Images are numbered in a stable filename-sorted order. Review contact-sheet.jpg and manifest.csv before assigning tutorial scenes.\n",
        encoding="utf-8",
    )
    print((OUT / "SUMMARY.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
