"""Pure geometry helpers for feature-anchored polar Circos tracks and chords."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class SectorInterval:
    start: float
    end: float

    @property
    def span(self) -> float:
        return self.end - self.start

    @property
    def midpoint(self) -> float:
        return (self.start + self.end) / 2


@dataclass(frozen=True)
class ChordGeometry:
    start_angle: float
    end_angle: float
    inner_radius: float
    theta: np.ndarray
    radius: np.ndarray


def sector_intervals(sectors: list[str], counts: dict[str, int], *,
                     gap_degrees: float = 2.0, start_degrees: float = 0.0) -> dict[str, SectorInterval]:
    if not sectors or len(set(sectors)) != len(sectors):
        raise ValueError("sectors must be a non-empty ordered list of unique names")
    if not math.isfinite(gap_degrees) or not 0 <= gap_degrees < 30:
        raise ValueError("gap_degrees must be finite and in [0, 30)")
    if not math.isfinite(start_degrees):
        raise ValueError("start_degrees must be finite")
    if any(counts.get(name, 0) <= 0 for name in sectors):
        raise ValueError("each sector must contain at least one feature")
    total_gap = math.radians(gap_degrees) * len(sectors)
    if total_gap >= 2 * math.pi:
        raise ValueError("sector gaps consume the full circle")
    available = 2 * math.pi - total_gap
    total_features = sum(counts[name] for name in sectors)
    cursor = math.radians(start_degrees)
    output: dict[str, SectorInterval] = {}
    for name in sectors:
        end = cursor + available * counts[name] / total_features
        output[name] = SectorInterval(cursor, end)
        cursor = end + math.radians(gap_degrees)
    return output


def feature_angles(features: list[dict[str, Any]], intervals: dict[str, SectorInterval], *,
                   pad_fraction: float = 0.02) -> dict[tuple[str, str], float]:
    """Place every observed feature monotonically within its ordered sector span."""
    if not 0 <= pad_fraction < 0.25:
        raise ValueError("pad_fraction must be in [0, 0.25)")
    output: dict[tuple[str, str], float] = {}
    for sector, arc in intervals.items():
        rows = sorted((row for row in features if row["sector"] == sector),
                      key=lambda row: (float(row["_score"]), row["feature_id"]))
        if not rows:
            raise ValueError(f"sector {sector!r} has no features")
        pad = arc.span * pad_fraction
        for i, row in enumerate(rows):
            key = (sector, row["feature_id"])
            if key in output:
                raise ValueError(f"duplicate feature anchor {key!r}")
            output[key] = arc.start + pad + (i + 0.5) / len(rows) * (arc.span - 2 * pad)
    return output


def score_radii(features: list[dict[str, Any]], *, inner_radius: float, outer_radius: float,
                baseline: float = 0.0, scale: float | None = None,
                signed: bool = False) -> tuple[dict[tuple[str, str], float], dict[str, float]]:
    """Map numeric scores to radial positions without discarding sign."""
    if not 0 < inner_radius < outer_radius:
        raise ValueError("score track radii must satisfy 0 < inner_radius < outer_radius")
    if not math.isfinite(baseline):
        raise ValueError("score baseline must be finite")
    values = [float(row["_score"]) for row in features]
    if not signed and any(value < 0 for value in values):
        raise ValueError("negative scores require signed=True")
    if not signed and baseline != 0:
        raise ValueError("a non-zero baseline requires signed=True")
    if signed:
        deviations = [abs(value - baseline) for value in values]
        observed_scale = max(deviations, default=0.0)
        used_scale = scale if scale is not None else observed_scale or 1.0
        if not math.isfinite(used_scale) or used_scale <= 0:
            raise ValueError("score scale must be finite and positive")
        if observed_scale > used_scale:
            raise ValueError("an observed score exceeds the configured symmetric scale")
        zero_radius = (inner_radius + outer_radius) / 2
        half_span = (outer_radius - inner_radius) / 2
        radii = { (row["sector"], row["feature_id"]): zero_radius +
                 half_span * (float(row["_score"]) - baseline) / used_scale for row in features }
    else:
        observed_scale = max((value - baseline for value in values), default=0.0)
        used_scale = scale if scale is not None else observed_scale or 1.0
        if not math.isfinite(used_scale) or used_scale <= 0:
            raise ValueError("score scale must be finite and positive")
        if any(value < baseline for value in values):
            raise ValueError("non-negative score is below the configured baseline")
        if observed_scale > used_scale:
            raise ValueError("an observed score exceeds the configured scale")
        zero_radius = inner_radius
        span = outer_radius - inner_radius
        radii = {(row["sector"], row["feature_id"]): inner_radius + span *
                 (float(row["_score"]) - baseline) / used_scale for row in features}
    return radii, {"baseline": baseline, "scale": float(used_scale),
                   "observed_max_deviation": float(observed_scale), "baseline_radius": zero_radius,
                   "signed": signed}


def cubic_chord(theta_start: float, theta_end: float, inner_radius: float, *,
                tension: float = 0.72, bundle_offset: float = 0.0,
                samples: int = 81) -> ChordGeometry:
    """Sample a cubic Bezier in polar coordinates with an open, non-zero center."""
    if not all(math.isfinite(value) for value in (theta_start, theta_end, inner_radius, tension, bundle_offset)):
        raise ValueError("chord geometry parameters must be finite")
    if inner_radius <= 0 or not 0.45 <= tension <= 0.85 or abs(bundle_offset) > 0.12:
        raise ValueError("require inner_radius>0, tension in [0.45, 0.85], and |bundle_offset|<=0.12")
    if samples < 5:
        raise ValueError("samples must be at least 5")
    delta = (theta_end - theta_start + math.pi) % (2 * math.pi) - math.pi
    end = theta_start + delta
    control_radius = inner_radius * (1 - tension)
    p0 = np.array([theta_start, inner_radius])
    p1 = np.array([theta_start + delta / 3 + bundle_offset, control_radius])
    p2 = np.array([theta_start + 2 * delta / 3 + bundle_offset, control_radius])
    p3 = np.array([end, inner_radius])
    t = np.linspace(0.0, 1.0, samples)[:, None]
    curve = ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 +
             3 * (1 - t) * t**2 * p2 + t**3 * p3)
    return ChordGeometry(theta_start, end, inner_radius, curve[:, 0], curve[:, 1])


def link_geometry(links: list[dict[str, Any]], anchors: dict[tuple[str, str], float], *,
                  inner_radius: float, tension: float = 0.72,
                  bundle_strength: float = 0.02) -> list[ChordGeometry]:
    if not 0 <= bundle_strength <= 0.12:
        raise ValueError("bundle_strength must be in [0, 0.12]")
    result = []
    for i, link in enumerate(links):
        source_key = (link["from_sector"], link["from_feature"])
        target_key = (link["to_sector"], link["to_feature"])
        if source_key not in anchors or target_key not in anchors:
            raise ValueError(f"missing feature anchor for link {source_key!r} -> {target_key!r}")
        # Stable alternating lanes separate dense links without moving their endpoints.
        lane = ((i % 9) - 4) / 4 if bundle_strength else 0.0
        offset = lane * bundle_strength
        result.append(cubic_chord(anchors[source_key], anchors[target_key], inner_radius,
                                  tension=tension, bundle_offset=offset))
    return result
