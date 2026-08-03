#!/usr/bin/env python3
"""Audit scientific figure exports for RGB/DPI/vector companions and hashes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from PIL import Image


IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _dpi(image: Image.Image) -> tuple[float, float]:
    value = image.info.get("dpi", (0, 0))
    if isinstance(value, tuple): return float(value[0] or 0), float(value[1] or 0)
    return float(value or 0), float(value or 0)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""): digest.update(block)
    return digest.hexdigest()


def inspect(root: Path, require_vector: bool = True) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXT):
        if path.name.endswith("_ai_base.png"):
            rows.append({"file": str(path), "kind": "AI_SOURCE_ASSET", "status": "EXCLUDED_SOURCE_ASSET", "notes": "conceptual source only"})
            continue
        with Image.open(path) as image:
            dpi_x, dpi_y = _dpi(image)
            base = path.with_suffix("")
            pdf_ok = base.with_suffix(".pdf").exists()
            svg_ok = base.with_suffix(".svg").exists()
            rgb_ok = image.mode == "RGB"
            dpi_ok = dpi_x >= 299 and dpi_y >= 299
            vector_ok = pdf_ok and svg_ok if require_vector else True
            status = "PASS" if rgb_ok and dpi_ok and vector_ok else "FAIL"
            rows.append({
                "file": str(path), "kind": "FINAL_FIGURE", "status": status,
                "mode": image.mode, "width_px": image.width, "height_px": image.height,
                "dpi_x": round(dpi_x, 2), "dpi_y": round(dpi_y, 2),
                "rgb_ok": rgb_ok, "dpi_ok": dpi_ok, "pdf_ok": pdf_ok, "svg_ok": svg_ok,
                "sha256": _sha256(path), "size_mb": round(path.stat().st_size / (1024 * 1024), 3),
            })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("figure_dir", type=Path)
    parser.add_argument("--output", type=Path, help="TSV output path")
    parser.add_argument("--json", type=Path, help="JSON manifest output path")
    parser.add_argument("--allow-missing-vector", action="store_true", help="do not require PDF and SVG siblings")
    args = parser.parse_args()
    rows = inspect(args.figure_dir.expanduser().resolve(), require_vector=not args.allow_missing_vector)
    fields = sorted({key for row in rows for key in row})
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)
    else:
        print("\t".join(fields));
        for row in rows: print("\t".join(str(row.get(field, "")) for field in fields))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True); args.json.write_text(json.dumps(rows, indent=2) + "\n")
    finals = [row for row in rows if row["kind"] == "FINAL_FIGURE"]
    failures = [row for row in finals if row["status"] == "FAIL"]
    excluded = sum(row["kind"] == "AI_SOURCE_ASSET" for row in rows)
    print(f"final_assets={len(finals)} failures={len(failures)} source_assets_excluded={excluded}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
