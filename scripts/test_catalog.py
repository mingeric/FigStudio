#!/usr/bin/env python3
"""Smoke-test every registered recipe and verify the rendered files."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from figure_studio import CATALOG, export_figure, render_kind


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--out-dir", type=Path, required=True); parser.add_argument("--limit", type=int, default=129)
    args = parser.parse_args(); args.out_dir.mkdir(parents=True, exist_ok=True)
    names = list(CATALOG)[:args.limit]
    for i, name in enumerate(names):
        if name == "circos_lollipop_chord":
            examples = Path(__file__).resolve().parents[1] / "examples" / "circos"
            fig = render_kind(name, seed=i, scores=examples / "gene_scores.csv", links=examples / "links.csv", sectors=examples / "sectors.csv")
        else:
            fig = render_kind(name, seed=i)
        export_figure(fig, args.out_dir / name, ["png"])
        plt.close(fig)
    expected = {f"{name}.png" for name in names}; actual = {p.name for p in args.out_dir.glob("*.png")}
    missing = sorted(expected - actual)
    print(f"recipes_tested={len(names)} files_written={len(actual)} missing={len(missing)}")
    if missing: print("missing=" + ",".join(missing))
    return 0 if not missing else 1


if __name__ == "__main__": raise SystemExit(main())
