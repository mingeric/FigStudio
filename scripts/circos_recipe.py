"""Data validation and native Matplotlib renderer for a Circos composite."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import is_color_like

BLUE, CORAL, TEAL = "#527FA6", "#C87570", "#568D88"
INK, PALE, GRID = "#454B50", "#F1F3F4", "#C9CED1"
ALLOWED_DIRECTIONS = {"up", "down", "risk", "protective", "neutral"}


def _csv(path: Path, required: set[str], name: str) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"{name}: file not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        missing = sorted(required - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"{name}: missing required columns: {', '.join(missing)}")
        return [{k: (v or "").strip() for k, v in row.items()} for row in reader]


def load_data(scores_path: Path, links_path: Path, sectors_path: Path | None = None,
              *, signed_scores: bool = False) -> dict[str, Any]:
    scores = _csv(scores_path, {"sector", "gene", "score", "direction"}, "gene_scores.csv")
    if not scores:
        raise ValueError("gene_scores.csv: at least one score row is required")
    seen_scores: set[tuple[str, str]] = set()
    for line, row in enumerate(scores, 2):
        if not row["sector"] or not row["gene"]:
            raise ValueError(f"gene_scores.csv row {line}: sector and gene must be non-empty")
        key = row["sector"], row["gene"]
        if key in seen_scores:
            raise ValueError(f"gene_scores.csv row {line}: duplicate sector/gene {key!r}")
        seen_scores.add(key)
        try:
            row["_score"] = float(row["score"])
        except ValueError as exc:
            raise ValueError(f"gene_scores.csv row {line}: score must be numeric") from exc
        if not math.isfinite(row["_score"]):
            raise ValueError(f"gene_scores.csv row {line}: score must be finite")
        if not signed_scores and row["_score"] < 0:
            raise ValueError(f"gene_scores.csv row {line}: negative score requires --signed-scores")
        if row["direction"].lower() not in ALLOWED_DIRECTIONS:
            raise ValueError(f"gene_scores.csv row {line}: unknown direction {row['direction']!r}; expected {', '.join(sorted(ALLOWED_DIRECTIONS))}")
        if row.get("label_priority"):
            try:
                priority = float(row["label_priority"])
            except ValueError as exc:
                raise ValueError(f"gene_scores.csv row {line}: label_priority must be numeric") from exc
            if not math.isfinite(priority):
                raise ValueError(f"gene_scores.csv row {line}: label_priority must be finite")
        if row.get("sample_size"):
            try:
                sample_size = float(row["sample_size"])
            except ValueError as exc:
                raise ValueError(f"gene_scores.csv row {line}: sample_size must be a positive integer") from exc
            if not math.isfinite(sample_size) or sample_size < 1 or not sample_size.is_integer():
                raise ValueError(f"gene_scores.csv row {line}: sample_size must be a positive integer")

    links = _csv(links_path, {"source_sector", "target_sector"}, "links.csv")
    link_keys: set[tuple[str, str, str]] = set()
    for line, row in enumerate(links, 2):
        for column in ("source_sector", "target_sector"):
            if not row[column]:
                raise ValueError(f"links.csv row {line}: {column} must be non-empty")
        try:
            row["_weight"] = float(row.get("weight") or 1)
        except ValueError as exc:
            raise ValueError(f"links.csv row {line}: weight must be numeric") from exc
        if not math.isfinite(row["_weight"]) or row["_weight"] <= 0:
            raise ValueError(f"links.csv row {line}: weight must be finite and positive")
        key = row["source_sector"], row["target_sector"], row.get("feature", "")
        if key in link_keys:
            raise ValueError(f"links.csv row {line}: duplicate ambiguous link {key!r}")
        link_keys.add(key)

    names = list(dict.fromkeys(row["sector"] for row in scores))
    for row in links:
        for column in ("source_sector", "target_sector"):
            if row[column] not in names:
                raise ValueError(f"links.csv: {column} {row[column]!r} does not exist in gene_scores.csv")
    meta: dict[str, dict[str, Any]] = {}
    if sectors_path:
        for line, row in enumerate(_csv(sectors_path, {"sector"}, "sectors.csv"), 2):
            name = row["sector"]
            if not name or name not in names:
                raise ValueError(f"sectors.csv row {line}: sector {name!r} is absent from gene_scores.csv")
            if name in meta:
                raise ValueError(f"sectors.csv row {line}: duplicate sector {name!r}")
            try:
                order = float(row["order"]) if row.get("order") else float(len(meta))
                if not math.isfinite(order):
                    raise ValueError
            except ValueError as exc:
                raise ValueError(f"sectors.csv row {line}: order must be finite numeric") from exc
            color = row.get("color", "")
            if color and not is_color_like(color):
                raise ValueError(f"sectors.csv row {line}: invalid color {color!r}")
            meta[name] = {"name": row.get("display_name") or name, "order": order, "color": color or None}
    for name in names:
        meta.setdefault(name, {"name": name, "order": float(len(meta)), "color": None})
    names.sort(key=lambda s: (meta[s]["order"], s))
    return {"scores": scores, "links": links, "sectors": names, "sector_meta": meta,
            "signed_scores": signed_scores}


def render(data: dict[str, Any], *, top_n: int = 4, gap_degrees: float = 3,
           link_limit: int = 500, baseline: float = 0, figsize: float = 8,
           label_orientation: str = "tangent", inner_radius: float = .48,
           outer_radius: float = .83, max_label_chars: int = 18,
           score_scale: float | None = None) -> plt.Figure:
    if top_n < 0 or link_limit < 0 or not 0 <= gap_degrees < 30:
        raise ValueError("top_n/link_limit must be non-negative and gap_degrees must be in [0, 30)")
    if label_orientation not in {"tangent", "radial"}:
        raise ValueError("label_orientation must be tangent or radial")
    if max_label_chars < 4:
        raise ValueError("max_label_chars must be at least 4")
    if not .05 < inner_radius < outer_radius < .95:
        raise ValueError("track radii must satisfy 0.05 < inner_radius < outer_radius < 0.95")
    if not math.isfinite(baseline) or not math.isfinite(figsize) or figsize <= 0:
        raise ValueError("baseline must be finite and figsize must be finite and positive")
    scores, links, sectors = data["scores"], data["links"], data["sectors"]
    if len(sectors) * gap_degrees >= 300:
        raise ValueError("gap_degrees leaves too little space for this number of sectors")
    fig = plt.figure(figsize=(figsize, figsize), facecolor="white")
    ax = fig.add_subplot(111, projection="polar", facecolor="white")
    ax.set_theta_direction(-1); ax.set_theta_offset(math.pi / 2); ax.set_ylim(0, 1.36); ax.set_axis_off()
    counts = {s: sum(r["sector"] == s for r in scores) for s in sectors}
    free = 2 * math.pi - math.radians(gap_degrees) * len(sectors)
    spans = {s: free * counts[s] / len(scores) for s in sectors}
    starts: dict[str, float] = {}; ends: dict[str, float] = {}; mids: dict[str, float] = {}
    cursor = 0.0
    for sector in sectors:
        starts[sector] = cursor; ends[sector] = cursor + spans[sector]
        mids[sector] = (starts[sector] + ends[sector]) / 2
        cursor = ends[sector] + math.radians(gap_degrees)

    max_deviation = max((abs(float(r["_score"]) - baseline) for r in scores), default=0)
    if score_scale is not None and (not math.isfinite(score_scale) or score_scale <= 0):
        raise ValueError("scale must be finite and positive")
    if score_scale is not None and max_deviation > score_scale:
        raise ValueError("an observed score exceeds --scale; increase the scale to avoid clipping")
    scale = score_scale if score_scale is not None else (max_deviation or 1)
    inner, outer = inner_radius, outer_radius
    signed = data.get("signed_scores", False)
    baseline_radius = (inner + outer) / 2 if signed else inner
    anchors: dict[tuple[str, str], float] = {}
    for index, sector in enumerate(sectors):
        info = data["sector_meta"][sector]
        rows = sorted((r for r in scores if r["sector"] == sector), key=lambda r: (float(r["_score"]), r["gene"]))
        start, end, width = starts[sector], ends[sector], spans[sector]
        pad = width * 0.025
        color = info["color"] or ("#DCE8EF" if index % 2 == 0 else "#E8E2E0")
        ax.bar(mids[sector], .10, width=width, bottom=.99, color=PALE, edgecolor=INK, linewidth=.55, zorder=2)
        tangent = (180 - math.degrees(mids[sector]) + 180) % 360 - 180
        if tangent < -90: tangent += 180
        if tangent > 90: tangent -= 180
        ax.text(mids[sector], 1.04, info["name"], rotation=tangent, rotation_mode="anchor", ha="center", va="center", fontsize=8, color=INK, clip_on=False)
        ax.bar(mids[sector], .07, width=width, bottom=.90, color=color, edgecolor=INK, linewidth=.55, zorder=2)
        for fraction in (.25, .5, .75, 1):
            if signed:
                tick_radius = inner + (outer-inner)*fraction
                ax.plot([start + pad, end - pad], [tick_radius]*2, color=GRID, lw=.35, zorder=0)
            else:
                ax.plot([start + pad, end - pad], [inner + (outer-inner)*fraction]*2, color=GRID, lw=.35, zorder=0)
        if signed:
            ax.plot([start + pad, end - pad], [baseline_radius]*2, color="#899196", lw=.5, ls="--", zorder=1)
        for j, row in enumerate(rows):
            theta = start + pad + (j + .5) / len(rows) * (width - 2*pad)
            anchors[(sector, row["gene"])] = theta
            value = float(row["_score"])
            displacement = min(1, abs(value-baseline)/scale)
            radius = baseline_radius + ((outer-inner)/2 * displacement * (1 if value >= baseline else -1)) if signed else inner + (outer-inner)*displacement
            direction = row["direction"].lower()
            marker = BLUE if direction in {"up", "risk"} else CORAL if direction in {"down", "protective"} else TEAL
            ax.plot([theta, theta], [inner, radius], color="#899196", lw=.45, zorder=2)
            ax.scatter([theta], [radius], s=12, color=marker, edgecolors="white", linewidths=.25, zorder=3)
        ranked = sorted(rows, key=lambda r: (float(r.get("label_priority") or 0), abs(float(r["_score"])-baseline), r["gene"]), reverse=True)
        selected = sorted(ranked[:top_n], key=lambda r: anchors[(sector, r["gene"])])
        label_angles = (np.linspace(start + pad*2, end - pad*2, len(selected))
                        if len(selected) > 1 else ([mids[sector]] if selected else []))
        for li, (row, label_theta) in enumerate(zip(selected, label_angles)):
            theta = anchors[(sector, row["gene"])]; label = row.get("display_label") or row["gene"]
            if len(label) > max_label_chars:
                label = label[:max_label_chars - 1].rstrip() + "…"
            value = float(row["_score"])
            displacement = min(1, abs(value-baseline)/scale)
            marker_radius = baseline_radius + ((outer-inner)/2 * displacement * (1 if value >= baseline else -1)) if signed else inner + (outer-inner)*displacement
            left = math.cos(label_theta) < 0; label_r = 1.18 + (li % 2) * .055
            ax.plot([theta, theta, label_theta, label_theta], [marker_radius, 1.105, 1.105, label_r-.02], color="#858B8F", lw=.4, zorder=3)
            radial_angle = 90 - math.degrees(label_theta)
            rotation = radial_angle if label_orientation == "radial" else radial_angle + 90
            rotation = (rotation + 180) % 360 - 180
            if rotation < -90: rotation += 180
            if rotation > 90: rotation -= 180
            ax.text(label_theta, label_r, label, rotation=rotation, rotation_mode="anchor", ha="right" if left else "left", va="center", fontsize=6.5, color=INK, clip_on=False)

    # Direct polar curves keep links in the same geometry as the tracks and labels.
    max_weight = max((r["_weight"] for r in links), default=1) or 1
    ordered = sorted(links, key=lambda r: (r["source_sector"], r["target_sector"], r.get("feature", "")))[:link_limit]
    for row in ordered:
        source, target, feature = row["source_sector"], row["target_sector"], row.get("feature", "")
        a = anchors.get((source, feature), mids[source]); b = anchors.get((target, feature), mids[target])
        delta = (b-a+math.pi) % (2*math.pi)-math.pi
        theta = a + np.linspace(0, 1, 45)*delta
        radius = (inner - .04) * (1 - np.sin(np.linspace(0, math.pi, 45))**.85)
        weight = row["_weight"]
        ax.plot(theta, radius, color=TEAL, alpha=.12+.32*weight/max_weight, lw=.35+weight/max_weight, zorder=1, solid_capstyle="round")

    legend = [plt.Line2D([], [], marker="o", ls="", color=BLUE, markersize=4, label="up / risk"),
              plt.Line2D([], [], marker="o", ls="", color=CORAL, markersize=4, label="down / protective"),
              plt.Line2D([], [], marker="o", ls="", color=TEAL, markersize=4, label="neutral")]
    fig.legend(handles=legend, title="Direction class", loc="lower center", ncol=3, frameon=False, fontsize=7, title_fontsize=7, bbox_to_anchor=(.5, .025))
    scale_text = f"{scale:g}" if max_deviation else "0 (all scores at baseline)"
    score_legend = (f"Score baseline {baseline:g} at dashed midline; max deviation {scale_text}; scale ±{scale:g}" if signed
                    else f"Score radius: baseline {baseline:g}; max deviation {scale_text}; scale {scale:g}")
    fig.text(.5, .085, f"{score_legend} | Links: shared feature association; width ∝ weight", ha="center", fontsize=6.5, color=INK)
    fig.subplots_adjust(left=.03, right=.97, top=.97, bottom=.14)
    return fig


def hashes(paths: list[Path]) -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths if path is not None}


def write_metadata(path: Path, input_sha256: dict[str, str], config: dict[str, Any], status: str) -> None:
    payload = {"schema_version": "1.0", "input_sha256": input_sha256, "configuration": config,
               "software": {"python": platform.python_version(), "matplotlib": matplotlib.__version__, "numpy": np.__version__},
               "data_status": status}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
