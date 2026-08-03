#!/usr/bin/env python3
"""Native scientific figure recipe catalog and deterministic renderer.

This module is deliberately dependency-light: matplotlib and numpy are enough
for the smoke-test catalog. Replace the demo arrays with project-native arrays
in a manuscript plotting script and keep the figure contract beside it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


BG = "#FAFBFD"
GRID = "#DDE5EC"
INK = "#203A57"
MUTED = "#74869A"
BLUE = "#5C88B4"
TEAL = "#39A39A"
ROSE = "#D98991"
BRICK = "#BE6D66"
PURPLE = "#8E7FBD"
ORANGE = "#E9A15C"
GOLD = "#D4AA52"
PALETTE = [BLUE, TEAL, ROSE, PURPLE, ORANGE, GOLD]


CATALOG_GROUPS: dict[str, tuple[str, ...]] = {
    "distributions": (
        "boxplot", "violin_plot", "strip_plot", "swarm_plot", "raincloud_plot", "ridge_plot",
        "histogram", "kde_density", "ecdf", "beeswarm", "sina_plot", "dot_distribution",
        "lollipop_distribution", "ridgeline_density", "empirical_cdf", "quantile_plot",
        "half_violin", "letter_value_plot",
    ),
    "comparisons": (
        "grouped_bar", "stacked_bar", "100pct_stacked_bar", "diverging_bar", "dumbbell",
        "slopegraph", "paired_dot", "interval_dot", "forest_plot", "caterpillar_plot",
        "tornado_plot", "waterfall", "bullet_chart", "radial_bar", "boxen_plot", "errorbar_summary",
    ),
    "associations": (
        "scatter_plot", "regression_plot", "hexbin_plot", "bubble_plot", "scatter_density",
        "marginal_scatter", "correlogram", "pairplot_matrix", "volcano_plot", "ma_plot", "qq_plot",
        "bland_altman", "concordance_plot", "lollipop_correlation", "joint_density", "contour_scatter",
        "residual_plot", "partial_residual",
    ),
    "multivariate": (
        "pca_scores", "pca_loadings", "umap_embedding", "tsne_embedding", "factor_analysis",
        "biplot", "parallel_coordinates", "radar_chart", "ternary_plot", "mds_embedding",
        "lda_embedding", "trajectory_plot", "sankey", "decision_boundary", "calibration_curve",
        "coefficient_path",
    ),
    "matrices": (
        "heatmap", "clustered_heatmap", "annotated_heatmap", "correlation_matrix", "confusion_matrix",
        "distance_matrix", "adjacency_matrix", "tile_plot", "bubble_matrix", "dot_heatmap",
        "zscore_heatmap", "oncoprint", "missingness_matrix", "pairwise_effect_matrix",
        "enrichment_heatmap", "matrix_profile",
    ),
    "networks": (
        "network_graph", "force_directed_graph", "circular_network", "chord_diagram", "arc_diagram",
        "hive_plot", "bipartite_network", "alluvial_flow", "sankey_flow", "pathway_map",
        "ligand_receptor_network", "source_target_flow", "edge_bundled_graph", "tree_dendrogram",
        "phylogeny_tree", "evidence_ladder",
    ),
    "temporal_survival": (
        "time_series", "multi_series", "area_chart", "stacked_area", "streamgraph", "event_timeline",
        "spaghetti_plot", "control_chart", "cumulative_incidence", "kaplan_meier", "survival_forest",
        "risk_table",
    ),
    "genomics_spatial_mechanism": (
        "protein_track", "mutation_lollipop", "genome_track", "chromosome_ideogram", "circos_overview",
        "variant_burden", "allele_frequency_spectrum", "spatial_feature", "spatial_grid", "spatial_hexbin",
        "spatial_dotplot", "image_quantification", "cell_type_composition", "ligand_receptor_lollipop",
        "mechanism_schematic", "graphical_abstract",
    ),
}

CATALOG: dict[str, str] = {
    name: group for group, names in CATALOG_GROUPS.items() for name in names
}
assert len(CATALOG) == 128, f"catalog must contain 128 unique recipes, found {len(CATALOG)}"


def _style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.titleweight": "bold",
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.facecolor": BG,
        "figure.facecolor": BG,
        "savefig.facecolor": BG,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.dpi": 350,
    })


def _title(ax: plt.Axes, kind: str) -> None:
    ax.set_title(kind.replace("_", " ").title(), loc="left", color=INK, pad=5)
    ax.grid(color=GRID, linewidth=0.45, alpha=0.8)


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _category(ax: plt.Axes, values: np.ndarray, labels: Iterable[str] | None = None) -> None:
    labels = list(labels or ["A", "B", "C", "D", "E"])
    x = np.arange(len(values))
    ax.bar(x, values, color=PALETTE[:len(values)], alpha=0.9)
    ax.set_xticks(x, labels)


def _draw_distribution(ax: plt.Axes, kind: str, rng: np.random.Generator) -> None:
    groups = [rng.normal(mu, 0.12 + i * 0.015, 28) for i, mu in enumerate([0.30, 0.48, 0.62])]
    labels = ["control", "context", "stress"]
    if kind in {"boxplot", "boxen_plot", "letter_value_plot"}:
        ax.boxplot(groups, patch_artist=True,
                   boxprops={"facecolor": BLUE, "alpha": 0.65}, medianprops={"color": INK, "linewidth": 1.2})
        ax.set_xticks(range(1, 4), labels)
    elif kind in {"violin_plot", "half_violin", "ridge_plot", "ridgeline_density"}:
        parts = ax.violinplot(groups, positions=np.arange(1, 4), showmeans=True, showextrema=False)
        for body, color in zip(parts["bodies"], PALETTE[:3]):
            body.set_facecolor(color); body.set_alpha(0.55); body.set_edgecolor("none")
        ax.set_xticks(range(1, 4), labels)
    elif kind in {"histogram", "kde_density", "ecdf", "empirical_cdf", "quantile_plot"}:
        for data, color, label in zip(groups, PALETTE[:3], labels):
            if kind == "histogram":
                ax.hist(data, bins=12, alpha=0.34, color=color, label=label)
            else:
                y = np.sort(data); x = np.linspace(0, 1, len(y))
                ax.plot(y, x, color=color, label=label)
        ax.legend(frameon=False, fontsize=7)
        ax.set_xlabel("value"); ax.set_ylabel("density / empirical fraction")
    else:
        for i, data in enumerate(groups):
            jitter = rng.normal(0, 0.055, len(data))
            ax.scatter(np.full(len(data), i) + jitter, data, s=14, alpha=0.65, color=PALETTE[i])
        ax.set_xticks(range(3), labels)
    _title(ax, kind)


def _draw_comparison(ax: plt.Axes, kind: str, rng: np.random.Generator) -> None:
    labels = ["A", "B", "C", "D", "E"]
    values = np.array([0.42, 0.67, 0.55, 0.80, 0.36]) + rng.normal(0, 0.035, 5)
    x = np.arange(5)
    if kind in {"forest_plot", "caterpillar_plot", "interval_dot", "errorbar_summary"}:
        lo = values - rng.uniform(0.07, 0.15, 5); hi = values + rng.uniform(0.07, 0.15, 5)
        ax.errorbar(values, x, xerr=[values - lo, hi - values], fmt="o", color=BLUE, ecolor=MUTED, capsize=3)
        ax.axvline(0.5, color=BRICK, linestyle="--", linewidth=0.8); ax.set_yticks(x, labels); ax.set_xlabel("effect / estimate")
    elif kind in {"dumbbell", "slopegraph", "paired_dot"}:
        a = values - rng.uniform(0.12, 0.28, 5); b = values
        for i, (u, v) in enumerate(zip(a, b)):
            ax.plot([u, v], [i, i], color=GRID, linewidth=2); ax.scatter([u, v], [i, i], color=[BLUE, ROSE], s=28, zorder=3)
        ax.set_yticks(x, labels); ax.set_xlabel("condition A → condition B")
    elif kind in {"diverging_bar", "tornado_plot", "waterfall"}:
        signed = values - 0.58; ax.barh(x, signed, color=[BLUE if v < 0 else ROSE for v in signed]); ax.axvline(0, color=INK, lw=0.8); ax.set_yticks(x, labels)
    elif kind == "stacked_bar" or kind == "100pct_stacked_bar":
        left = np.zeros(5)
        for color in PALETTE[:3]:
            part = rng.uniform(0.1, 0.45, 5)
            if kind == "100pct_stacked_bar": part = part / np.maximum(part + 0.75, 1e-6)
            ax.bar(x, part, bottom=left, color=color, alpha=0.8); left += part
        ax.set_xticks(x, labels)
    elif kind == "radial_bar":
        theta = np.linspace(0, 2 * np.pi, 5, endpoint=False); figure = ax.figure; position = ax.get_position(); ax.remove(); ax = figure.add_axes(position, polar=True)
        ax.bar(theta, values, width=0.8, color=PALETTE[:5], alpha=0.75); ax.set_xticks(theta, labels)
    else:
        _category(ax, values, labels)
    _title(ax, kind)


def _draw_association(ax: plt.Axes, kind: str, rng: np.random.Generator) -> None:
    x = rng.normal(0, 1, 120); y = 0.58 * x + rng.normal(0, 0.75, 120)
    if kind in {"volcano_plot", "ma_plot"}:
        x = rng.uniform(-3, 3, 120); y = rng.uniform(0, 8, 120)
        ax.scatter(x, y, s=14, color=np.where(y > 5, ROSE, BLUE), alpha=0.65)
        ax.axhline(5, color=BRICK, ls="--", lw=0.8); ax.axvline(0, color=GRID, lw=0.8)
        ax.set_xlabel("effect size" if kind == "volcano_plot" else "mean abundance"); ax.set_ylabel("−log10 P")
    elif kind == "qq_plot":
        q = np.sort(rng.normal(size=120)); expected = np.linspace(q.min(), q.max(), 120); ax.scatter(expected, q, s=12, color=BLUE); ax.plot(expected, expected, color=BRICK, ls="--")
        ax.set_xlabel("expected quantile"); ax.set_ylabel("observed quantile")
    elif kind in {"hexbin_plot", "scatter_density", "joint_density", "contour_scatter"}:
        ax.hexbin(x, y, gridsize=18, cmap="GnBu", mincnt=1); ax.set_xlabel("feature 1"); ax.set_ylabel("feature 2")
    elif kind in {"correlogram", "pairplot_matrix"}:
        matrix = rng.normal(size=(5, 5)); matrix = (matrix + matrix.T) / 2; np.fill_diagonal(matrix, 1)
        ax.imshow(matrix, cmap="RdBu_r", vmin=-1, vmax=1); ax.set_xticks(range(5), list("ABCDE")); ax.set_yticks(range(5), list("ABCDE"))
    elif kind in {"bland_altman", "concordance_plot"}:
        mean = (x + y) / 2; diff = x - y; ax.scatter(mean, diff, s=14, color=TEAL, alpha=0.65); ax.axhline(diff.mean(), color=INK); ax.axhline(diff.mean() + 1.96 * diff.std(), color=BRICK, ls="--"); ax.axhline(diff.mean() - 1.96 * diff.std(), color=BRICK, ls="--"); ax.set_xlabel("mean"); ax.set_ylabel("difference")
    elif kind == "lollipop_correlation":
        labels = list("ABCDE"); vals = np.sort(rng.uniform(-0.75, 0.85, 5)); ax.hlines(range(5), 0, vals, color=GRID); ax.scatter(vals, range(5), color=[BLUE if v < 0 else ROSE for v in vals], s=32); ax.axvline(0, color=INK, lw=0.8); ax.set_yticks(range(5), labels); ax.set_xlabel("Spearman ρ")
    else:
        ax.scatter(x, y, s=16, color=BLUE, alpha=0.6); coef = np.polyfit(x, y, 1); ax.plot(x, coef[0] * x + coef[1], color=BRICK, lw=1.4); ax.set_xlabel("feature 1"); ax.set_ylabel("feature 2")
    _title(ax, kind)


def _draw_multivariate(ax: plt.Axes, kind: str, rng: np.random.Generator) -> None:
    groups = rng.integers(0, 3, 180); centers = np.array([[-1, -0.3], [0.5, 0.8], [1.2, -0.8]])
    pts = centers[groups] + rng.normal(0, 0.28, (len(groups), 2))
    if kind in {"pca_scores", "umap_embedding", "tsne_embedding", "mds_embedding", "lda_embedding", "factor_analysis", "biplot"}:
        for i, color in enumerate(PALETTE[:3]): ax.scatter(*pts[groups == i].T, s=12, alpha=0.6, color=color, label=f"group {i+1}")
        ax.legend(frameon=False, fontsize=6); ax.set_xlabel("component 1"); ax.set_ylabel("component 2")
    elif kind in {"parallel_coordinates", "coefficient_path"}:
        x = np.arange(6)
        for i in range(8): ax.plot(x, np.cumsum(rng.normal(0, 0.35, 6)), color=PALETTE[i % 6], alpha=0.6)
        ax.set_xticks(x, [f"v{i}" for i in x])
    elif kind == "radar_chart":
        theta = np.linspace(0, 2 * np.pi, 6, endpoint=False); vals = rng.uniform(0.3, 1, 6); figure = ax.figure; position = ax.get_position(); ax.remove(); polar = figure.add_axes(position, polar=True); polar.plot(np.r_[theta, theta[0]], np.r_[vals, vals[0]], color=TEAL); polar.fill(np.r_[theta, theta[0]], np.r_[vals, vals[0]], color=TEAL, alpha=0.25); polar.set_xticks(theta, list("ABCDEF")); ax = polar
    elif kind == "ternary_plot":
        data = rng.dirichlet([2, 3, 4], 80); ax.scatter(data[:, 0] + 0.5 * data[:, 1], data[:, 1] * 0.86, s=14, color=PURPLE, alpha=0.65); ax.set_xlabel("component A/B"); ax.set_ylabel("component B")
    elif kind == "decision_boundary":
        xx, yy = np.meshgrid(np.linspace(-2, 2, 80), np.linspace(-2, 2, 80)); z = xx + 0.7 * yy; ax.contourf(xx, yy, z > 0, levels=[-0.1, 0.1, 1], colors=["#DCEAF3", "#F3DDE0"], alpha=0.8); ax.scatter(*pts.T, c=groups, cmap="tab10", s=10)
    elif kind == "calibration_curve":
        p = np.linspace(0.02, 0.98, 12); ax.plot(p, p, "--", color=INK); ax.plot(p, p ** 0.8, "o-", color=TEAL); ax.set_xlabel("predicted probability"); ax.set_ylabel("observed frequency")
    else:
        ax.plot(np.arange(6), rng.uniform(0, 1, 6), color=BLUE, marker="o")
    _title(ax, kind)


def _draw_matrix(ax: plt.Axes, kind: str, rng: np.random.Generator) -> None:
    matrix = rng.normal(0, 1, (8, 9));
    if kind in {"correlation_matrix", "confusion_matrix", "adjacency_matrix", "pairwise_effect_matrix"}: matrix = np.corrcoef(rng.normal(size=(9, 80)))
    if kind in {"missingness_matrix", "oncoprint"}: matrix = rng.integers(0, 4 if kind == "oncoprint" else 2, (8, 14))
    cmap = "RdBu_r" if kind not in {"oncoprint", "missingness_matrix"} else "Set2"
    ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=None if kind in {"oncoprint", "missingness_matrix"} else -2, vmax=None if kind in {"oncoprint", "missingness_matrix"} else 2)
    ax.set_xticks(range(matrix.shape[1]), [str(i + 1) for i in range(matrix.shape[1])], rotation=55, ha="right", fontsize=6)
    ax.set_yticks(range(matrix.shape[0]), [f"g{i + 1}" for i in range(matrix.shape[0])])
    if kind in {"annotated_heatmap", "correlation_matrix", "confusion_matrix"}:
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                if matrix.shape[1] <= 10: ax.text(j, i, f"{matrix[i, j]:.1f}", ha="center", va="center", fontsize=5, color=INK)
    _title(ax, kind)


def _draw_network(ax: plt.Axes, kind: str, rng: np.random.Generator) -> None:
    n = 10; theta = np.linspace(0, 2 * np.pi, n, endpoint=False); radius = 1.0 if kind not in {"hive_plot", "circular_network", "chord_diagram"} else 1.15
    pos = np.c_[radius * np.cos(theta), radius * np.sin(theta)]
    edges = [(i, (i + 1) % n) for i in range(n)] + [(i, (i + 3) % n) for i in range(0, n, 2)]
    for i, j in edges:
        if kind in {"arc_diagram", "chord_diagram", "circular_network"}:
            xs = np.linspace(pos[i, 0], pos[j, 0], 60); base = np.linspace(0, 1, 60); ys = (1 - base) * pos[i, 1] + base * pos[j, 1] + 0.28 * np.sin(np.pi * base); ax.plot(xs, ys, color=GRID, lw=0.9)
        else:
            ax.plot(pos[[i, j], 0], pos[[i, j], 1], color=GRID, lw=1)
    ax.scatter(pos[:, 0], pos[:, 1], s=rng.uniform(80, 180, n), c=[PALETTE[i % 6] for i in range(n)], edgecolor="white", linewidth=0.8, zorder=3)
    for i, (x, y) in enumerate(pos): ax.text(x * 1.12, y * 1.12, f"N{i + 1}", ha="center", va="center", fontsize=6, color=INK)
    ax.set_aspect("equal"); ax.axis("off"); _title(ax, kind)


def _draw_temporal(ax: plt.Axes, kind: str, rng: np.random.Generator) -> None:
    t = np.arange(30); lines = [np.cumsum(rng.normal(0.02, 0.15, 30)) for _ in range(3)]
    if kind in {"kaplan_meier", "cumulative_incidence"}:
        for i, color in enumerate(PALETTE[:3]): ax.step(t, np.exp(-0.03 * (t + 1) * (i + 1)), where="post", color=color, label=f"stratum {i + 1}")
        ax.set_ylim(0, 1.05); ax.set_ylabel("survival / cumulative probability"); ax.legend(frameon=False, fontsize=6)
    elif kind in {"area_chart", "stacked_area", "streamgraph"}:
        layers = np.abs(rng.normal(size=(3, 30))); ax.stackplot(t, layers, colors=PALETTE[:3], alpha=0.75)
    elif kind == "event_timeline":
        for i, (tt, label) in enumerate(zip([4, 9, 16, 23], ["context", "response", "sampling", "release"])):
            ax.axvline(tt, color=PALETTE[i], lw=2); ax.text(tt, i * 0.12, label, rotation=90, va="bottom", ha="right", fontsize=6)
        ax.set_ylim(-0.05, 0.5)
    elif kind == "risk_table":
        for i in range(3): ax.plot(t, 90 - i * 24 - 2 * t, color=PALETTE[i], lw=2); ax.scatter(t[::5], 90 - i * 24 - 2 * t[::5], color=PALETTE[i], s=14)
        ax.set_yticks([90, 66, 42], ["group 1", "group 2", "group 3"])
    else:
        for i, line in enumerate(lines): ax.plot(t, line, color=PALETTE[i], alpha=0.8, label=f"series {i + 1}")
        ax.legend(frameon=False, fontsize=6); ax.set_xlabel("time")
    _title(ax, kind)


def _draw_genomics(ax: plt.Axes, kind: str, rng: np.random.Generator) -> None:
    if kind in {"mechanism_schematic", "graphical_abstract"}:
        ax.axis("off"); boxes = [(0.08, 0.42, 0.22, 0.20, "context"), (0.39, 0.42, 0.22, 0.20, "SMC5/6 state"), (0.70, 0.42, 0.22, 0.20, "observed output")]
        for i, (x, y, w, h, label) in enumerate(boxes):
            ax.add_patch(plt.Rectangle((x, y), w, h, transform=ax.transAxes, facecolor=["#E6F1F6", "#E8F3EE", "#F3E9F0"][i], edgecolor=PALETTE[i], linewidth=1.5, joinstyle="round")); ax.text(x + w / 2, y + h / 2, label, transform=ax.transAxes, ha="center", va="center", color=INK, fontsize=9, weight="bold")
            if i < 2: ax.annotate("", xy=(boxes[i + 1][0] - 0.02, y + h / 2), xytext=(x + w + 0.02, y + h / 2), xycoords=ax.transAxes, arrowprops={"arrowstyle": "->", "color": PALETTE[i], "lw": 1.5})
        ax.text(0.5, 0.23, "CONCEPTUAL MODEL / EVIDENCE BOUNDARY", transform=ax.transAxes, ha="center", color=MUTED, fontsize=7, weight="bold")
    elif kind in {"protein_track", "genome_track", "chromosome_ideogram", "circos_overview"}:
        for y, color, label in zip([0.25, 0.5, 0.75], PALETTE[:3], ["domain", "feature", "variant"]):
            ax.plot([0, 1], [y, y], color=INK, lw=2); positions = rng.uniform(0.03, 0.97, 7); ax.scatter(positions, np.full(7, y), color=color, s=28, zorder=3); ax.text(1.01, y, label, transform=ax.transAxes, va="center", fontsize=7)
        ax.set_xlim(0, 1); ax.set_yticks([]); ax.set_xlabel("coordinate / genomic position")
    elif kind in {"spatial_feature", "spatial_grid", "spatial_hexbin", "spatial_dotplot", "image_quantification"}:
        x, y = rng.uniform(0, 1, (2, 400)); value = np.sin(8 * x) + np.cos(7 * y); ax.scatter(x, y, c=value, cmap="RdBu_r", s=16, alpha=0.7); ax.set_xlabel("x position"); ax.set_ylabel("y position")
    elif kind in {"mutation_lollipop", "ligand_receptor_lollipop"}:
        x = np.arange(1, 14); y = rng.uniform(0.1, 1, 13); ax.vlines(x, 0, y, color=GRID); ax.scatter(x, y, color=ROSE, s=35); ax.set_xlabel("position"); ax.set_ylabel("frequency / score")
    else:
        values = rng.uniform(0.1, 1, 6); _category(ax, values, [f"C{i + 1}" for i in range(6)])
    _title(ax, kind)


def render_kind(kind: str, *, seed: int = 0, ax: plt.Axes | None = None) -> plt.Figure:
    if kind not in CATALOG: raise ValueError(f"Unknown recipe {kind!r}; use `catalog` to list 128 recipes")
    _style(); own = ax is None
    fig = plt.figure(figsize=(183 / 25.4, 105 / 25.4), facecolor=BG) if own else ax.figure
    target = ax or fig.add_subplot(111)
    rng = _rng(seed)
    group = CATALOG[kind]
    if group == "distributions": _draw_distribution(target, kind, rng)
    elif group == "comparisons": _draw_comparison(target, kind, rng)
    elif group == "associations": _draw_association(target, kind, rng)
    elif group == "multivariate": _draw_multivariate(target, kind, rng)
    elif group == "matrices": _draw_matrix(target, kind, rng)
    elif group == "networks": _draw_network(target, kind, rng)
    elif group == "temporal_survival": _draw_temporal(target, kind, rng)
    else: _draw_genomics(target, kind, rng)
    return fig


def _save_rgb_raster(path: Path, dpi: int, *, tiff: bool = False) -> None:
    from PIL import Image

    with Image.open(path) as image:
        rgb = image.convert("RGB")
        if tiff: rgb.save(path, dpi=(dpi, dpi), compression="tiff_lzw")
        else: rgb.save(path, dpi=(dpi, dpi))


def export_figure(fig: plt.Figure, out: Path, formats: Iterable[str]) -> list[Path]:
    out.parent.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for fmt in formats:
        fmt = fmt.lower().lstrip(".")
        path = out.with_suffix(f".{fmt}")
        if fmt in {"pdf", "svg"}: fig.savefig(path, format=fmt, bbox_inches="tight", facecolor=BG)
        elif fmt == "png": fig.savefig(path, format=fmt, dpi=350, bbox_inches="tight", facecolor=BG); _save_rgb_raster(path, 350)
        elif fmt in {"tif", "tiff"}: fig.savefig(path, format="tiff", dpi=600, bbox_inches="tight", facecolor=BG); _save_rgb_raster(path, 600, tiff=True)
        else: raise ValueError(f"Unsupported format: {fmt}")
        saved.append(path)
    return saved


def cmd_catalog(args: argparse.Namespace) -> int:
    if args.json:
        print(json.dumps([{"name": name, "group": group} for name, group in CATALOG.items()], indent=2))
    else:
        print(f"recipes={len(CATALOG)}")
        for group, names in CATALOG_GROUPS.items(): print(f"\n[{group}]\n" + "  " + "\n  ".join(names))
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    fig = render_kind(args.kind, seed=args.seed)
    saved = export_figure(fig, Path(args.out), args.formats.split(","))
    plt.close(fig)
    print(json.dumps({"kind": args.kind, "seed": args.seed, "files": [str(p) for p in saved]}, indent=2))
    return 0


def cmd_contact(args: argparse.Namespace) -> int:
    names = list(CATALOG)[args.start:args.start + args.limit]
    cols = max(1, args.columns); rows = math.ceil(len(names) / cols)
    _style(); fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.2, rows * 2.25), squeeze=False, facecolor=BG)
    for i, name in enumerate(names): render_kind(name, seed=args.seed + i, ax=axes.flat[i]); axes.flat[i].set_title(name.replace("_", " "), fontsize=6.5, loc="left", color=INK)
    for ax in axes.flat[len(names):]: ax.axis("off")
    path = Path(args.out).with_suffix(".png"); path.parent.mkdir(parents=True, exist_ok=True); fig.savefig(path, dpi=180, bbox_inches="tight", facecolor=BG); _save_rgb_raster(path, 180); plt.close(fig)
    print(json.dumps({"count": len(names), "file": str(path)}, indent=2))
    return 0


def cmd_prompt(args: argparse.Namespace) -> int:
    print(f"Use case: scientific-educational\nAsset type: conceptual mechanism schematic / graphical abstract\nPrimary request: {args.request}\nStyle/medium: text-free pale scientific illustration; final labels will be added by vector code\nComposition/framing: wide left-to-right context → SMC5/6 state → measured output\nColor palette: near-white canvas, pale blue/teal/rose semantic accents\nConstraints: no quantitative axes, no invented data, no causal arrow unless supported\nAvoid: text baked into the AI base, rainbow palette, clinical or therapeutic implication, watermark")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scientific Figure Studio: 128 recipes, exports, and mechanism prompt scaffolding")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("catalog", help="list the 128 plot recipes"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_catalog)
    p = sub.add_parser("render", help="render one deterministic recipe"); p.add_argument("--kind", required=True, choices=sorted(CATALOG)); p.add_argument("--out", required=True); p.add_argument("--seed", type=int, default=0); p.add_argument("--formats", default="pdf,svg,png,tiff"); p.set_defaults(func=cmd_render)
    p = sub.add_parser("contact-sheet", help="render a catalog contact sheet"); p.add_argument("--out", required=True); p.add_argument("--limit", type=int, default=32); p.add_argument("--start", type=int, default=0); p.add_argument("--columns", type=int, default=4); p.add_argument("--seed", type=int, default=0); p.set_defaults(func=cmd_contact)
    p = sub.add_parser("mechanism-prompt", help="print built-in imagegen prompt scaffolding"); p.add_argument("--request", default="a bounded scientific mechanism linking a measured state to context-specific outputs"); p.set_defaults(func=cmd_prompt)
    return parser


if __name__ == "__main__":
    parsed = build_parser().parse_args()
    raise SystemExit(parsed.func(parsed))
