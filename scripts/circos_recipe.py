"""Validated, feature-anchored native Matplotlib Circos composite."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import shutil
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import is_color_like

from circos_geometry import feature_angles, link_geometry, score_radii, sector_intervals

BLUE = "#2878A8"
CORAL = "#D97862"
TEAL = "#456F6B"
NEUTRAL = "#78858A"
INK = "#3F484C"
GRID = "#D6DADD"
SECTOR_PALE = "#ECEFF0"
DIRECTION_COLORS = {
    "positive": BLUE, "up": BLUE, "risk": BLUE,
    "negative": CORAL, "down": CORAL, "protective": CORAL,
    "neutral": NEUTRAL,
}
SCHEMA_VERSION = "2.0"


def _read_csv(path: Path, required: set[str], name: str) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"{name}: file not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        missing = sorted(required - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"{name}: missing required columns: {', '.join(missing)}")
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


def _optional_float(row: dict[str, str], column: str, *, low: float | None = None,
                    high: float | None = None, row_number: int, table: str) -> float | None:
    raw = row.get(column, "")
    if raw == "":
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{table} row {row_number}: {column} must be numeric") from exc
    if not math.isfinite(value) or (low is not None and value < low) or (high is not None and value > high):
        limit = f" in [{low:g}, {high:g}]" if low is not None and high is not None else " finite"
        raise ValueError(f"{table} row {row_number}: {column} must be{limit}")
    return value


def _sector_metadata(sectors_path: Path | None, names: list[str], table_name: str = "sectors.csv") -> tuple[list[str], dict[str, dict[str, Any]]]:
    metadata: dict[str, dict[str, Any]] = {}
    if sectors_path is not None:
        rows = _read_csv(sectors_path, {"sector"}, table_name)
        for line, row in enumerate(rows, 2):
            sector = row["sector"]
            if not sector or sector not in names:
                raise ValueError(f"{table_name} row {line}: sector {sector!r} is absent from feature data")
            if sector in metadata:
                raise ValueError(f"{table_name} row {line}: duplicate sector {sector!r}")
            order = _optional_float(row, "order", row_number=line, table=table_name)
            color = row.get("color", "")
            if color and not is_color_like(color):
                raise ValueError(f"{table_name} row {line}: invalid color {color!r}")
            metadata[sector] = {"name": row.get("display_name") or sector,
                                "order": order if order is not None else float(len(metadata)),
                                "color": color or None}
    for sector in names:
        metadata.setdefault(sector, {"name": sector, "order": float(len(metadata)), "color": None})
    names.sort(key=lambda sector: (metadata[sector]["order"], sector))
    return names, metadata


def _validate(features: list[dict[str, str]], raw_links: list[dict[str, str]],
              sectors_path: Path | None, *, signed_scores: bool,
              feature_table: str = "features.csv", link_table: str = "links.csv",
              legacy: bool = False) -> dict[str, Any]:
    if not features:
        raise ValueError(f"{feature_table}: at least one feature row is required")
    feature_keys: set[tuple[str, str]] = set()
    feature_sectors: dict[str, set[str]] = {}
    normalized_features: list[dict[str, Any]] = []
    for line, row in enumerate(features, 2):
        sector, feature_id = row.get("sector", ""), row.get("feature_id", "")
        if not sector or not feature_id:
            raise ValueError(f"{feature_table} row {line}: sector and feature_id must be non-empty")
        key = (sector, feature_id)
        if key in feature_keys:
            raise ValueError(f"{feature_table} row {line}: duplicate (sector, feature_id) {key!r}")
        feature_keys.add(key)
        feature_sectors.setdefault(feature_id, set()).add(sector)
        try:
            score = float(row.get("score", ""))
        except ValueError as exc:
            raise ValueError(f"{feature_table} row {line}: score is missing or not numeric") from exc
        if not math.isfinite(score):
            raise ValueError(f"{feature_table} row {line}: score must be finite")
        if score < 0 and not signed_scores:
            raise ValueError(f"{feature_table} row {line}: negative score requires --signed-scores")
        direction = row.get("direction", "").strip().lower()
        if direction not in DIRECTION_COLORS:
            raise ValueError(f"{feature_table} row {line}: unknown direction {direction!r}; expected positive, negative, or neutral (legacy aliases up/down/risk/protective are accepted)")
        fdr = _optional_float(row, "fdr", low=0, high=1, row_number=line, table=feature_table)
        p_value = _optional_float(row, "p_value", low=0, high=1, row_number=line, table=feature_table)
        effect = _optional_float(row, "effect_size", row_number=line, table=feature_table)
        rank = _optional_float(row, "rank", row_number=line, table=feature_table)
        legacy_priority = _optional_float(row, "_legacy_priority", row_number=line, table=feature_table)
        normalized_features.append({**row, "sector": sector, "feature_id": feature_id,
                                    "label": row.get("label") or feature_id, "direction": direction,
                                    "_score": score, "_fdr": fdr, "_p_value": p_value,
                                    "_effect": effect, "_rank": rank,
                                    "_legacy_priority": legacy_priority})

    sector_names = list(dict.fromkeys(row["sector"] for row in normalized_features))
    link_keys: dict[tuple[tuple[str, str], tuple[str, str]], dict[str, Any]] = {}
    normalized_links: list[dict[str, Any]] = []
    duplicate_links_removed = 0
    for line, row in enumerate(raw_links, 2):
        from_sector = row.get("from_sector", "").strip()
        to_sector = row.get("to_sector", "").strip()
        from_feature = row.get("from_feature", "").strip()
        to_feature = row.get("to_feature", "").strip()
        if not all((from_sector, to_sector, from_feature, to_feature)):
            raise ValueError(f"{link_table} row {line}: from/to sector and feature anchors are required; unanchored sector-only links are not accepted")
        raw_weight = row.get("weight", "").strip()
        try:
            weight = float(raw_weight) if raw_weight else 1.0
        except ValueError as exc:
            raise ValueError(f"{link_table} row {line}: weight must be numeric") from exc
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError(f"{link_table} row {line}: weight must be finite and positive")
        if from_sector == to_sector:
            raise ValueError(f"{link_table} row {line}: inter-sector links must connect different sectors")
        source_key, target_key = (from_sector, from_feature), (to_sector, to_feature)
        if source_key not in feature_keys:
            raise ValueError(f"{link_table} row {line}: source anchor {source_key!r} is absent from {feature_table}")
        if target_key not in feature_keys:
            raise ValueError(f"{link_table} row {line}: target anchor {target_key!r} is absent from {feature_table}")
        link_type = row.get("link_type", "").strip() or "shared_feature"
        if link_type == "shared_feature":
            if from_feature != to_feature:
                raise ValueError(f"{link_table} row {line}: shared_feature links require identical feature IDs")
            if len(feature_sectors.get(from_feature, set())) < 2:
                raise ValueError(f"{link_table} row {line}: shared feature {from_feature!r} must occur in at least two sectors")
        pair = tuple(sorted((source_key, target_key)))
        current = {"from_sector": from_sector, "from_feature": from_feature,
                   "to_sector": to_sector, "to_feature": to_feature,
                   "link_type": link_type, "_weight": weight}
        if pair in link_keys:
            prior = link_keys[pair]
            if prior["link_type"] != link_type or not math.isclose(prior["_weight"], weight):
                raise ValueError(f"{link_table} row {line}: duplicate undirected endpoint pair has conflicting type or weight: {pair!r}")
            duplicate_links_removed += 1
            continue
        link_keys[pair] = current
        normalized_links.append(current)

    sector_names, sector_meta = _sector_metadata(sectors_path, sector_names)
    normalized_links.sort(key=lambda row: (row["from_sector"], row["from_feature"], row["to_sector"], row["to_feature"], row["link_type"]))
    return {"features": normalized_features, "scores": normalized_features,
            "links": normalized_links, "sectors": sector_names, "sector_meta": sector_meta,
            "signed_scores": signed_scores,
            "provenance": {"schema_version": "1.0-legacy" if legacy else SCHEMA_VERSION,
                           "feature_rows_input": len(features), "feature_rows_used": len(normalized_features),
                           "link_rows_input": len(raw_links), "links_after_deduplication": len(normalized_links),
                           "duplicate_undirected_links_removed": duplicate_links_removed,
                           "link_rows_removed_by_validation": 0}}


def load_features_data(features_path: Path, links_path: Path,
                       sectors_path: Path | None = None, *, signed_scores: bool = False) -> dict[str, Any]:
    features = _read_csv(features_path, {"sector", "feature_id", "score", "direction"}, "features.csv")
    links = _read_csv(links_path, {"from_sector", "from_feature", "to_sector", "to_feature"}, "links.csv")
    return _validate(features, links, sectors_path, signed_scores=signed_scores)


def load_legacy_data(scores_path: Path, links_path: Path,
                     sectors_path: Path | None = None, *, signed_scores: bool = False) -> dict[str, Any]:
    """Compatibility adapter for V1 gene_scores/source_sector tables."""
    score_rows = _read_csv(scores_path, {"sector", "gene", "score", "direction"}, "gene_scores.csv")
    features = []
    for row in score_rows:
        features.append({"sector": row["sector"], "feature_id": row["gene"],
                         "score": row["score"], "direction": row["direction"],
                         "label": row.get("display_label") or row["gene"],
                         "fdr": row.get("fdr", ""), "p_value": row.get("p_value", ""),
                         "effect_size": row.get("effect_size", ""),
                         "_legacy_priority": str(-float(row["label_priority"])) if row.get("label_priority") else ""})
    old_links = _read_csv(links_path, {"source_sector", "target_sector"}, "legacy links.csv")
    links = []
    for line, row in enumerate(old_links, 2):
        feature = row.get("feature", "").strip()
        if not feature:
            raise ValueError(f"legacy links.csv row {line}: feature is required; V1 sector-only midpoint links cannot be carried forward")
        links.append({"from_sector": row["source_sector"], "from_feature": feature,
                      "to_sector": row["target_sector"], "to_feature": feature,
                      "weight": row.get("weight", ""), "link_type": "shared_feature"})
    return _validate(features, links, sectors_path, signed_scores=signed_scores,
                     feature_table="gene_scores.csv", link_table="legacy links.csv", legacy=True)


def load_data(scores_path: Path, links_path: Path, sectors_path: Path | None = None,
              *, signed_scores: bool = False) -> dict[str, Any]:
    """Retained V1 callable API; V2 callers should use load_features_data."""
    return load_legacy_data(scores_path, links_path, sectors_path, signed_scores=signed_scores)


def _rank_key(row: dict[str, Any], baseline: float) -> tuple[Any, ...]:
    fdr = row.get("_fdr")
    p_value = row.get("_p_value")
    effect = abs(row.get("_effect") or 0.0)
    score_effect = abs(float(row["_score"]) - baseline)
    if row.get("_rank") is not None:
        return (0, row["_rank"], fdr if fdr is not None else 1.0,
                p_value if p_value is not None else 1.0, -effect, -score_effect, row["feature_id"])
    if row.get("_legacy_priority") is not None:
        return (0, row["_legacy_priority"], fdr if fdr is not None else 1.0,
                p_value if p_value is not None else 1.0, -effect, -score_effect, row["feature_id"])
    significance = fdr if fdr is not None else p_value if p_value is not None else 1.0
    return (1, significance, -effect, -score_effect, row["feature_id"])


def _display_label(row: dict[str, Any], limit: int) -> str:
    label = str(row.get("label") or row["feature_id"])
    return label if len(label) <= limit else label[:limit - 1].rstrip() + "…"


def _collision_placements(features: list[dict[str, Any]], anchors: dict[tuple[str, str], float],
                          intervals: dict[str, Any], *, top_k: int, max_chars: int,
                          font_size: float, figure_inches: float, label_radius: float,
                          baseline: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for sector, arc in intervals.items():
        rows = sorted((row for row in features if row["sector"] == sector), key=lambda row: _rank_key(row, baseline))
        for row in rows[top_k:]:
            suppressed.append({**row, "suppression_reason": "below_top_k"})
        candidates.extend(rows[:top_k])
    candidates.sort(key=lambda row: (_rank_key(row, baseline), row["sector"], row["feature_id"]))
    placed: list[dict[str, Any]] = []
    # Radius in display space is normalized to the polar axes' outer limit.
    radius_inches = figure_inches * 0.39 * label_radius / (label_radius + .15)
    placed_widths: list[tuple[float, float]] = []
    for row in candidates:
        source = anchors[(row["sector"], row["feature_id"])]
        label = _display_label(row, max_chars)
        # Uppercase identifiers and digits occupy more width than spaces/punctuation.
        em_width = sum(.66 if c.isupper() else .57 if c.isdigit() else .38 if c in " _-." else .52 for c in label)
        half_angle = (em_width * font_size / 72 / radius_inches) / 2
        arc = intervals[row["sector"]]
        pad = arc.span * .015
        step = math.radians(1.0)
        max_shift = min(arc.span * .38, math.radians(18))
        offsets = [0.0]
        for tick in range(1, int(max_shift / step) + 1):
            offsets.extend([tick * step, -tick * step])
        slot = None
        for offset in offsets:
            angle = source + offset
            if not arc.start + pad <= angle <= arc.end - pad:
                continue
            required = half_angle + math.radians(1.4)
            if all(_angular_distance(angle, other_angle) >= required + other_half
                   for other_angle, other_half in placed_widths):
                slot = angle
                break
        if slot is None:
            suppressed.append({**row, "suppression_reason": "label_collision"})
        else:
            item = {**row, "display_text": label, "source_angle": source, "display_angle": slot,
                    "half_angle": half_angle}
            placed.append(item)
            placed_widths.append((slot, half_angle))
    return placed, suppressed


def _angular_distance(a: float, b: float) -> float:
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def _upright_rotation(theta: float, orientation: str, *, theta_offset: float = math.pi / 2) -> float:
    radial = math.degrees(theta_offset - theta)
    angle = radial if orientation == "radial" else radial + 90
    angle = (angle + 180) % 360 - 180
    if angle < -90:
        angle += 180
    if angle > 90:
        angle -= 180
    return angle


def render(data: dict[str, Any], *, top_n: int = 4, gap_degrees: float = 2.0,
           start_degrees: float = 0.0, link_limit: int | None = None,
           baseline: float = 0.0, score_scale: float | None = None,
           signed_scores: bool | None = None, width_mm: float = 180.0,
           figsize: float | None = None, label_orientation: str = "tangent",
           max_label_chars: int = 18, chord_tension: float = 0.72,
           bundle_strength: float = 0.025, data_status: str = "real") -> plt.Figure:
    if top_n < 0 or link_limit is not None and link_limit < 0:
        raise ValueError("top_k and link_limit must be non-negative")
    if label_orientation not in {"tangent", "radial"}:
        raise ValueError("label_orientation must be tangent or radial")
    if max_label_chars < 4:
        raise ValueError("max_label_chars must be at least 4")
    if not math.isfinite(width_mm) or not 50 <= width_mm <= 300:
        raise ValueError("width_mm must be finite and between 50 and 300")
    if not math.isfinite(start_degrees):
        raise ValueError("start_angle must be finite")
    features, links, sectors = data["features"], data["links"], data["sectors"]
    signed = data.get("signed_scores", False) if signed_scores is None else signed_scores
    figure_inches = figsize if figsize is not None else width_mm / 25.4
    if not math.isfinite(figure_inches) or figure_inches <= 0:
        raise ValueError("figure size must be finite and positive")
    counts = {sector: sum(row["sector"] == sector for row in features) for sector in sectors}
    intervals = sector_intervals(sectors, counts, gap_degrees=gap_degrees, start_degrees=start_degrees)

    score_inner, score_outer = 0.57, 0.87
    chord_radius = score_inner - 0.035
    sector_band_inner = score_outer + 0.035
    band_width = max(.045, .078 - .0025 * max(0, len(sectors) - 6))
    sector_band_outer = sector_band_inner + band_width
    label_radius = sector_band_outer + .11
    requested_labels = min(top_n * len(sectors), len(features))
    font_size = min(7.4, max(4.8, 7.5 - .18 * math.log2(max(1, len(sectors) / 6)) -
                             .28 * math.log2(max(1, requested_labels / 24))))
    max_radius = label_radius + .15
    anchors = feature_angles(features, intervals, pad_fraction=.02)
    radii, scale_info = score_radii(features, inner_radius=score_inner, outer_radius=score_outer,
                                    baseline=baseline, scale=score_scale, signed=signed)
    placed_labels, suppressed = _collision_placements(
        features, anchors, intervals, top_k=top_n, max_chars=max_label_chars,
        font_size=font_size, figure_inches=figure_inches, label_radius=label_radius,
        baseline=baseline)

    weight_values = [float(link["_weight"]) for link in links]
    weight_cap = float(np.percentile(weight_values, 95)) if weight_values else 1.0
    weight_cap = max(weight_cap, np.finfo(float).eps)
    ordered_links = sorted(links, key=lambda row: (-row["_weight"], row["from_sector"], row["from_feature"],
                                                   row["to_sector"], row["to_feature"], row["link_type"]))
    drawn_links = ordered_links if link_limit is None else ordered_links[:link_limit]
    link_curves = link_geometry(drawn_links, anchors, inner_radius=chord_radius,
                                 tension=chord_tension, bundle_strength=bundle_strength)

    fig = plt.figure(figsize=(figure_inches, figure_inches), facecolor="#FFFFFF")
    ax = fig.add_subplot(111, projection="polar", facecolor="#FFFFFF")
    ax.set_theta_direction(-1)
    ax.set_theta_offset(math.pi / 2)
    ax.set_ylim(0, max_radius)
    ax.set_axis_off()

    # Chords are sampled cubic Beziers in the same polar frame as every track.
    for link, curve in zip(drawn_links, link_curves):
        fraction = min(float(link["_weight"]), weight_cap) / weight_cap
        width = float(np.clip(.32 + .72 * math.sqrt(fraction), .32, 1.04))
        style = "-" if link["link_type"] == "shared_feature" else (0, (1.8, 1.1))
        ax.plot(curve.theta, curve.radius, color=TEAL, alpha=.42, linewidth=width,
                linestyle=style, zorder=1, solid_capstyle="round")

    tick_fractions = (-1, -.5, 0, .5, 1) if signed else (0, .25, .5, .75, 1)
    baseline_radius = scale_info["baseline_radius"]
    for sector in sectors:
        arc = intervals[sector]
        theta_grid = np.linspace(arc.start, arc.end, 90)
        for fraction in tick_fractions:
            radius = baseline_radius + fraction * ((score_outer - score_inner) / 2) if signed else score_inner + fraction * (score_outer - score_inner)
            color = "#AAB1B4" if signed and fraction == 0 else GRID
            style = "--" if signed and fraction == 0 else "-"
            ax.plot(theta_grid, np.full_like(theta_grid, radius), color=color,
                    linewidth=.48 if style == "--" else .34, linestyle=style, zorder=0)
        boundary_radius = np.linspace(chord_radius, sector_band_outer, 20)
        ax.plot([arc.start] * len(boundary_radius), boundary_radius, color=INK, linewidth=.48, zorder=4)
        ax.plot([arc.end] * len(boundary_radius), boundary_radius, color=INK, linewidth=.48, zorder=4)

    # One pale neutral sector band; no decorative stacked annuli.
    for sector in sectors:
        arc = intervals[sector]
        info = data["sector_meta"][sector]
        face = info["color"] or SECTOR_PALE
        ax.bar(arc.midpoint, band_width, width=arc.span, bottom=sector_band_inner,
               color=face, edgecolor="#646D71", linewidth=.48, align="center", zorder=4)
        name = str(info["name"])
        rotation = _upright_rotation(arc.midpoint, "tangent")
        ax.text(arc.midpoint, (sector_band_inner + sector_band_outer) / 2, name,
                rotation=rotation, rotation_mode="anchor", ha="center", va="center",
                fontsize=max(5.0, font_size - .25), color=INK, zorder=5, clip_on=False)

    # All score points and stems use the same sector-local feature anchor angles as links.
    for row in features:
        key = (row["sector"], row["feature_id"])
        theta, radius = anchors[key], radii[key]
        color = DIRECTION_COLORS[row["direction"]]
        ax.plot([theta, theta], [baseline_radius, radius], color=color, alpha=.58,
                linewidth=.42, zorder=2)
        marker_size = max(5, 12 * (figure_inches / (180 / 25.4)) ** 2)
        ax.scatter([theta], [radius], s=marker_size, color=color, edgecolors="#FFFFFF",
                   linewidths=.28, zorder=3)

    label_artists: list[tuple[dict[str, Any], Any, Any]] = []
    for index, item in enumerate(placed_labels):
        theta, display_theta = item["source_angle"], item["display_angle"]
        score_radius = radii[(item["sector"], item["feature_id"])]
        ring_radius = sector_band_outer + .035
        label_r = label_radius + (index % 2) * .035
        # Leaders begin at the actual point angle and route around the sector band.
        line, = ax.plot([theta, theta, display_theta], [score_radius, ring_radius, ring_radius],
                        color="#737C80", linewidth=.42, zorder=5)
        rotation = _upright_rotation(display_theta, label_orientation)
        side = "left" if math.cos(display_theta) >= 0 else "right"
        text_artist = ax.text(display_theta, label_r, item["display_text"], rotation=rotation,
                              rotation_mode="anchor", ha=side, va="center", fontsize=font_size,
                              color=INK, clip_on=False, zorder=6)
        label_artists.append((item, line, text_artist))

    # Explicit DEMO stamp prevents a screenshot from being detached from its synthetic-data note.
    if data_status == "demo":
        fig.text(.5, .965, "DEMO · SYNTHETIC DATA ONLY", ha="center", va="center",
                 fontsize=7, weight="bold", color="#A54E4A")

    direction_handles = [plt.Line2D([], [], marker="o", linestyle="", color=BLUE, markersize=4, label="positive / up / risk"),
                         plt.Line2D([], [], marker="o", linestyle="", color=CORAL, markersize=4, label="negative / down / protective"),
                         plt.Line2D([], [], marker="o", linestyle="", color=NEUTRAL, markersize=4, label="neutral")]
    link_types = sorted({row["link_type"] for row in drawn_links})
    link_handles = [plt.Line2D([], [], color=TEAL, linewidth=.8,
                               linestyle="-" if kind == "shared_feature" else "--",
                               label=f"{kind.replace('_', ' ')} links") for kind in link_types]
    handles = direction_handles + link_handles
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5, .035),
               ncol=min(4, max(1, len(handles))), frameon=False, fontsize=6.4,
               handlelength=1.4, columnspacing=1.0)
    tick_text = ", ".join(f"{baseline + fraction * scale_info['scale']:g}" for fraction in tick_fractions)
    score_mode = (f"signed: baseline={baseline:g}, scale=±{scale_info['scale']:g}"
                  if signed else f"non-negative: baseline={baseline:g}, scale={scale_info['scale']:g}")
    fig.text(.5, .105, f"Radial score ({score_mode}); tick values: {tick_text}",
             ha="center", va="center", fontsize=6.2, color=INK)
    cap_note = f"weight width capped at 95th percentile ({weight_cap:g})" if drawn_links else "no links supplied"
    fig.text(.5, .078, f"Links connect named feature anchors; link color is neutral teal; {cap_note}",
             ha="center", va="center", fontsize=5.9, color=INK)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_position([.14, .22, .72, .72])

    # Render once for display-space checks; clip/collision failures are recorded, not silently omitted.
    fig.canvas.draw()
    kept: list[tuple[dict[str, Any], Any, Any]] = []
    for item, line, text_artist in label_artists:
        box = text_artist.get_window_extent(renderer=fig.canvas.get_renderer())
        if box.x0 < 1 or box.y0 < 1 or box.x1 > fig.bbox.width - 1 or box.y1 > fig.bbox.height - 1:
            text_artist.remove(); line.remove()
            suppressed.append({**item, "suppression_reason": "outside_canvas"})
        else:
            kept.append((item, line, text_artist))
    kept_by_priority = sorted(kept, key=lambda triplet: (_rank_key(triplet[0], baseline), triplet[0]["sector"], triplet[0]["feature_id"]))
    final_kept: list[tuple[dict[str, Any], Any, Any]] = []
    for item, line, text_artist in kept_by_priority:
        box = text_artist.get_window_extent(renderer=fig.canvas.get_renderer())
        overlap = False
        for _, _, prior_artist in final_kept:
            prior = prior_artist.get_window_extent(renderer=fig.canvas.get_renderer())
            width = max(0, min(box.x1, prior.x1) - max(box.x0, prior.x0))
            height = max(0, min(box.y1, prior.y1) - max(box.y0, prior.y0))
            area = width * height
            smaller = min(max(1, box.width * box.height), max(1, prior.width * prior.height))
            if area / smaller > .01:
                overlap = True
                break
        if overlap:
            text_artist.remove(); line.remove()
            suppressed.append({**item, "suppression_reason": "display_bbox_overlap_gt_0.01"})
        else:
            final_kept.append((item, line, text_artist))

    observed_labels = len(final_kept)
    provenance = {**data["provenance"], "signed_scores": signed,
                  "baseline": baseline, "scale": scale_info["scale"],
                  "score_scale_method": "user-specified" if score_scale is not None else "max absolute deviation from baseline",
                  "track_radii": {"chord_endpoint": chord_radius, "score_inner": score_inner,
                                  "score_outer": score_outer, "sector_band_inner": sector_band_inner,
                                  "sector_band_outer": sector_band_outer, "label_radius": label_radius},
                  "features_drawn": len(features), "links_drawn": len(drawn_links),
                  "links_removed_by_limit": len(links) - len(drawn_links),
                  "label_candidates_top_k": requested_labels, "labels_drawn": observed_labels,
                  "labels_suppressed": len(suppressed), "label_collision_threshold": .01,
                  "label_suppression_reasons": {reason: sum(row.get("suppression_reason") == reason for row in suppressed)
                                                for reason in sorted({row.get("suppression_reason") for row in suppressed})},
                  "link_width_cap_p95": weight_cap, "aggregation": "none; feature-level endpoint links",
                  "minimum_chord_radius": min((float(curve.radius.min()) for curve in link_curves), default=None),
                  "feature_angle_contract": "sector-local feature anchors shared by scores, leaders, and links"}
    fig._circos_provenance = provenance
    fig._circos_suppressed = suppressed
    return fig


def hashes(paths: list[Path]) -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths if path is not None}


def _payload(input_sha256: dict[str, str], config: dict[str, Any], status: str) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "input_sha256": input_sha256,
            "configuration": config, "software": {"python": platform.python_version(),
            "matplotlib": matplotlib.__version__, "numpy": np.__version__},
            "data_status": status}


def write_metadata(path: Path, input_sha256: dict[str, str], config: dict[str, Any], status: str) -> None:
    path.write_text(json.dumps(_payload(input_sha256, config, status), indent=2) + "\n", encoding="utf-8")


def write_suppressed_labels(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = ["sector", "feature_id", "label", "score", "direction", "fdr", "p_value", "effect_size", "rank", "suppression_reason"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({"sector": row.get("sector"), "feature_id": row.get("feature_id"),
                             "label": row.get("label"), "score": row.get("_score"),
                             "direction": row.get("direction"), "fdr": row.get("_fdr"),
                             "p_value": row.get("_p_value"), "effect_size": row.get("_effect"),
                             "rank": row.get("_rank"), "suppression_reason": row.get("suppression_reason")})


def write_config_yaml(path: Path, config: dict[str, Any]) -> None:
    # JSON scalar syntax is valid YAML 1.2; this avoids an extra YAML runtime dependency.
    lines = [f"schema_version: {SCHEMA_VERSION}", "configuration:"]
    for key, value in config.items():
        lines.append(f"  {key}: {json.dumps(value, ensure_ascii=False)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def snapshot_inputs(out: Path, inputs: dict[str, Path | None]) -> dict[str, str]:
    copied: dict[str, str] = {}
    for label, source in inputs.items():
        if source is None:
            continue
        target = out.parent / f"{out.name}.source_{label}.csv"
        if target.resolve() != source.resolve():
            shutil.copy2(source, target)
        copied[label] = hashlib.sha256(target.read_bytes()).hexdigest()
    return copied


def write_run_manifest(path: Path, input_sha256: dict[str, str], output_sha256: dict[str, str],
                       config: dict[str, Any], status: str) -> None:
    payload = _payload(input_sha256, config, status)
    payload["output_sha256"] = output_sha256
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
