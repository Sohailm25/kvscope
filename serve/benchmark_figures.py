from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

_FAMILY_ORDER = {
    "aligned-prefix": 0,
    "near-aligned-prefix": 1,
    "mixed-long-short": 2,
    "bursty-arrivals": 3,
    "no-overlap-control": 4,
    "eviction-ordering": 5,
    "hotset-scan": 6,
    "locality-shift": 7,
    "locality-return": 8,
}

_COLORS = {
    "background": "#f7f3ea",
    "panel": "#fffaf2",
    "axis": "#2e2a24",
    "grid": "#d8cdbd",
    "text": "#201c18",
    "muted": "#6e6254",
    "cache_on": "#2d6a4f",
    "cache_off": "#b7b1a7",
    "delta_positive": "#d17b0f",
    "delta_negative": "#aa3a2a",
    "fifo": "#85725f",
    "lru": "#0b7285",
    "lfu": "#b65f0b",
}


def build_benchmark_figures_report(
    *,
    repo_root: Path,
    live_cache_report_path: Path,
    capacity_sweep_report_path: Path,
    report_slug: str,
) -> dict[str, Any]:
    live_cache_report = json.loads(live_cache_report_path.read_text())
    capacity_sweep_report = json.loads(capacity_sweep_report_path.read_text())

    figures = [
        _build_live_cache_figure(
            live_cache_report=live_cache_report,
            source_report_path=str(live_cache_report_path.relative_to(repo_root)),
        ),
        _build_policy_tradeoff_figure(
            capacity_sweep_report=capacity_sweep_report,
            source_report_path=str(capacity_sweep_report_path.relative_to(repo_root)),
        ),
    ]

    return {
        "schema_version": "benchmark-figures-v1",
        "report_slug": report_slug,
        "created_at_utc": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "source_reports": {
            "live_cache": str(live_cache_report_path.relative_to(repo_root)),
            "capacity_sweep": str(capacity_sweep_report_path.relative_to(repo_root)),
        },
        "figures": figures,
        "notes": [
            "These figures are generated from summary reports and remain subordinate to the underlying manifests, raw results, and report JSONs.",
            "The live-cache figure is about direct cache-hit visibility and prefill direction, while the replay figure is about policy surfaces as capacity changes.",
        ],
    }


def render_benchmark_figures_markdown(report: dict[str, Any]) -> str:
    lines = [
        "",
        f"# {report['report_slug']}",
        "",
        f"- Created: `{report['created_at_utc']}`",
        f"- Live cache source: `{report['source_reports']['live_cache']}`",
        f"- Capacity sweep source: `{report['source_reports']['capacity_sweep']}`",
        "",
        "## Figures",
        "",
    ]

    for figure in report["figures"]:
        lines.extend(
            [
                f"### `{figure['title']}`",
                "",
                f"- File: `{figure['figure_path']}`",
                f"- Kind: `{figure['kind']}`",
                f"- Source report: `{figure['source_report_path']}`",
                f"- Referenced runs: `{', '.join(figure['referenced_run_ids'])}`",
                f"- Caption: {figure['caption']}",
                "",
            ]
        )

    lines.extend(["## Notes", ""])
    for note in report["notes"]:
        lines.append(f"- {note}")

    return "\n".join(lines) + "\n"


def write_benchmark_figures_report(
    *,
    repo_root: Path,
    report: dict[str, Any],
    markdown: str,
) -> tuple[Path, Path, list[Path]]:
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    base_name = f"{timestamp}__serve__phase6__{report['report_slug']}"
    manifest_dir = repo_root / "artifacts" / "manifests"
    figure_dir = repo_root / "artifacts" / "figures"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    json_path = manifest_dir / f"{base_name}.json"
    markdown_path = manifest_dir / f"{base_name}.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    markdown_path.write_text(markdown)

    figure_paths: list[Path] = []
    for figure in report["figures"]:
        figure_path = repo_root / figure["figure_path"]
        figure_path.parent.mkdir(parents=True, exist_ok=True)
        if figure["kind"] == "live-cache-observability":
            _render_live_cache_png(figure_path=figure_path, figure=figure)
        elif figure["kind"] == "policy-tradeoffs":
            _render_policy_tradeoff_png(figure_path=figure_path, figure=figure)
        else:
            raise ValueError(f"unsupported figure kind: {figure['kind']}")
        figure_paths.append(figure_path)

    return json_path, markdown_path, figure_paths


def _build_live_cache_figure(
    *,
    live_cache_report: dict[str, Any],
    source_report_path: str,
) -> dict[str, Any]:
    families = [
        workload_family
        for workload_family, summary in sorted(
            live_cache_report["families"].items(),
            key=lambda item: (_FAMILY_ORDER.get(item[0], 999), item[0]),
        )
        if summary["cache_on"]["run_count"] > 0 and summary["cache_off"]["run_count"] > 0
    ]
    if not families:
        raise ValueError("live cache figure requires at least one family with cache-on and cache-off runs")

    rows = []
    referenced_run_ids: set[str] = set()
    for workload_family in families:
        summary = live_cache_report["families"][workload_family]
        cache_on = summary["cache_on"]
        cache_off = summary["cache_off"]
        rows.append(
            {
                "workload_family": workload_family,
                "cache_on_hit_rate": float(cache_on["prefix_cache_hit_rate"]["mean"]),
                "cache_off_hit_rate": float(cache_off["prefix_cache_hit_rate"]["mean"]),
                "prefill_delta_ms": round(
                    float(cache_off["request_prefill_mean_ms"]["mean"])
                    - float(cache_on["request_prefill_mean_ms"]["mean"]),
                    3,
                ),
            }
        )
        for mode_name in ("cache_on", "cache_off"):
            referenced_run_ids.update(
                run["run_id"] for run in summary[mode_name]["runs"]
            )

    return {
        "kind": "live-cache-observability",
        "title": "Live Cache Observability",
        "caption": (
            "Cache-on/off hit rates make direct reuse visible, while the prefill delta panel "
            "shows which families actually get a cleaner prefill story."
        ),
        "figure_path": "artifacts/figures/live-cache-toggle__vllm__cross-family__hit-rate-and-prefill.png",
        "source_report": live_cache_report["report_slug"],
        "source_report_path": source_report_path,
        "referenced_run_ids": sorted(referenced_run_ids),
        "workload_families": families,
        "rows": rows,
    }


def _build_policy_tradeoff_figure(
    *,
    capacity_sweep_report: dict[str, Any],
    source_report_path: str,
) -> dict[str, Any]:
    families = [
        workload_family
        for workload_family in (
            "eviction-ordering",
            "hotset-scan",
            "locality-shift",
            "locality-return",
        )
        if workload_family in capacity_sweep_report["families"]
    ]
    if not families:
        raise ValueError("policy tradeoff figure requires at least one capacity-sweep family")

    capacities = [int(capacity) for capacity in capacity_sweep_report["capacities"]]
    panels = []
    referenced_run_ids: set[str] = set()
    for workload_family in families:
        summary = capacity_sweep_report["families"][workload_family]
        panels.append(
            {
                "workload_family": workload_family,
                "fifo": [
                    float(summary["capacities"][str(capacity)]["policies"]["fifo"]["hit_rate_mean"])
                    for capacity in capacities
                ],
                "lru": [
                    float(summary["capacities"][str(capacity)]["policies"]["lru"]["hit_rate_mean"])
                    for capacity in capacities
                ],
                "lfu": [
                    float(summary["capacities"][str(capacity)]["policies"]["lfu"]["hit_rate_mean"])
                    for capacity in capacities
                ],
            }
        )
        referenced_run_ids.update(run["run_id"] for run in summary["runs"])

    caption = (
        "Replay hit-rate curves by capacity make three different behaviors visible: "
        "eviction-ordering separates LRU from FIFO, hotset-scan leaves LFU headroom above LRU, "
        "and locality-shift shows recency beating stale frequency."
    )
    if "locality-return" in families:
        caption = (
            "Replay hit-rate curves by capacity make four different behaviors visible: "
            "eviction-ordering separates LRU from FIFO, hotset-scan leaves LFU headroom above LRU, "
            "locality-shift shows recency beating stale frequency, and locality-return shows a "
            "capacity crossover between recency and frequency."
        )

    return {
        "kind": "policy-tradeoffs",
        "title": "Replay Policy Tradeoffs",
        "caption": caption,
        "figure_path": "artifacts/figures/policy-tradeoffs__vllm__cross-family__hit-rate-by-capacity.png",
        "source_report": capacity_sweep_report["report_slug"],
        "source_report_path": source_report_path,
        "referenced_run_ids": sorted(referenced_run_ids),
        "workload_families": families,
        "capacities": capacities,
        "panels": panels,
    }


def _render_live_cache_png(*, figure_path: Path, figure: dict[str, Any]) -> None:
    image_width = 1400
    image_height = 760
    image = Image.new("RGB", (image_width, image_height), _COLORS["background"])
    draw = ImageDraw.Draw(image)
    title_font, body_font, small_font = _fonts()

    _draw_title_block(
        draw=draw,
        title_font=title_font,
        body_font=body_font,
        title=figure["title"],
        subtitle=figure["caption"],
    )

    left_panel = (60, 150, 660, 620)
    right_panel = (740, 150, 1340, 620)
    _draw_panel(draw=draw, box=left_panel, title="Cache Hit Rate", subtitle="cache-on vs cache-off")
    _draw_panel(draw=draw, box=right_panel, title="Prefill Delta", subtitle="cache-off minus cache-on (ms)")

    rows = figure["rows"]
    max_hit_rate = max(
        [row["cache_on_hit_rate"] for row in rows] + [row["cache_off_hit_rate"] for row in rows] + [0.5]
    )
    max_prefill_delta = max(abs(row["prefill_delta_ms"]) for row in rows) or 1.0

    _draw_grouped_bar_panel(
        draw=draw,
        box=left_panel,
        rows=rows,
        left_key="cache_on_hit_rate",
        right_key="cache_off_hit_rate",
        left_label="on",
        right_label="off",
        left_color=_COLORS["cache_on"],
        right_color=_COLORS["cache_off"],
        max_value=max_hit_rate,
        font=body_font,
        small_font=small_font,
        suffix="",
    )
    _draw_delta_bar_panel(
        draw=draw,
        box=right_panel,
        rows=rows,
        value_key="prefill_delta_ms",
        max_abs_value=max_prefill_delta,
        font=body_font,
        small_font=small_font,
        positive_color=_COLORS["delta_positive"],
        negative_color=_COLORS["delta_negative"],
        suffix=" ms",
    )
    _draw_footer(
        draw=draw,
        font=small_font,
        report_slug=figure["source_report"],
        run_ids=figure["referenced_run_ids"],
        y=image_height - 30,
    )
    image.save(figure_path, format="PNG")


def _render_policy_tradeoff_png(*, figure_path: Path, figure: dict[str, Any]) -> None:
    panels = figure["panels"]
    if len(panels) <= 3:
        image_width = 1520
        image_height = 820
        panel_width = 440
        panel_height = 500
        gap_x = 30
        gap_y = 0
        columns = len(panels)
        rows = 1
        start_x = 60
        start_y = 170
    else:
        image_width = 1520
        image_height = 1120
        panel_width = 660
        panel_height = 390
        gap_x = 60
        gap_y = 40
        columns = 2
        rows = 2
        start_x = 70
        start_y = 170

    image = Image.new("RGB", (image_width, image_height), _COLORS["background"])
    draw = ImageDraw.Draw(image)
    title_font, body_font, small_font = _fonts()

    _draw_title_block(
        draw=draw,
        title_font=title_font,
        body_font=body_font,
        title=figure["title"],
        subtitle=figure["caption"],
    )

    for index, panel in enumerate(panels):
        row = index // columns
        column = index % columns
        left = start_x + column * (panel_width + gap_x)
        top = start_y + row * (panel_height + gap_y)
        box = (left, top, left + panel_width, top + panel_height)
        _draw_panel(
            draw=draw,
            box=box,
            title=panel["workload_family"],
            subtitle="Replay hit rate by capacity",
        )
        _draw_line_panel(
            draw=draw,
            box=box,
            capacities=figure["capacities"],
            panel=panel,
            font=body_font,
            small_font=small_font,
        )

    legend_y = start_y + rows * panel_height + (rows - 1) * gap_y + 30
    _draw_policy_legend(draw=draw, font=body_font, anchor=(60, legend_y))
    _draw_footer(
        draw=draw,
        font=small_font,
        report_slug=figure["source_report"],
        run_ids=figure["referenced_run_ids"],
        y=image_height - 30,
    )
    image.save(figure_path, format="PNG")


def _fonts() -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, ...]:
    try:
        title_font = ImageFont.truetype("Helvetica.ttc", 28)
        body_font = ImageFont.truetype("Helvetica.ttc", 18)
        small_font = ImageFont.truetype("Helvetica.ttc", 14)
    except OSError:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    return title_font, body_font, small_font


def _draw_title_block(
    *,
    draw: ImageDraw.ImageDraw,
    title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    body_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    title: str,
    subtitle: str,
) -> None:
    draw.text((60, 40), title, fill=_COLORS["text"], font=title_font)
    draw.text((60, 82), subtitle, fill=_COLORS["muted"], font=body_font)


def _draw_panel(
    *,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    subtitle: str,
) -> None:
    draw.rounded_rectangle(box, radius=20, fill=_COLORS["panel"], outline=_COLORS["grid"], width=2)
    draw.text((box[0] + 20, box[1] + 18), title, fill=_COLORS["text"], font=_fonts()[1])
    draw.text((box[0] + 20, box[1] + 42), subtitle, fill=_COLORS["muted"], font=_fonts()[2])


def _draw_grouped_bar_panel(
    *,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    rows: list[dict[str, Any]],
    left_key: str,
    right_key: str,
    left_label: str,
    right_label: str,
    left_color: str,
    right_color: str,
    max_value: float,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    small_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    suffix: str,
) -> None:
    chart = (box[0] + 50, box[1] + 90, box[2] - 30, box[3] - 70)
    _draw_y_axis(draw=draw, chart=chart, max_value=max_value, font=small_font, min_value=0.0)

    group_width = (chart[2] - chart[0]) / max(len(rows), 1)
    bar_width = group_width * 0.22
    for index, row in enumerate(rows):
        center_x = chart[0] + group_width * (index + 0.5)
        _draw_value_bar(
            draw=draw,
            chart=chart,
            center_x=int(center_x - bar_width * 0.7),
            bar_width=int(bar_width),
            value=float(row[left_key]),
            max_value=max_value,
            color=left_color,
        )
        _draw_value_bar(
            draw=draw,
            chart=chart,
            center_x=int(center_x + bar_width * 0.7),
            bar_width=int(bar_width),
            value=float(row[right_key]),
            max_value=max_value,
            color=right_color,
        )
        label = row["workload_family"].replace("-prefix", "").replace("-", "\n")
        _draw_multiline_centered(
            draw=draw,
            xy=(center_x, chart[3] + 10),
            text=label,
            fill=_COLORS["text"],
            font=small_font,
        )
        draw.text(
            (center_x - 28, chart[1] - 18),
            f"{row[left_key]:.3f}/{row[right_key]:.1f}{suffix}".rstrip("0").rstrip("."),
            fill=_COLORS["muted"],
            font=small_font,
        )

    _draw_panel_legend(
        draw=draw,
        font=small_font,
        items=[(left_label, left_color), (right_label, right_color)],
        anchor=(chart[0], box[3] - 40),
    )


def _draw_delta_bar_panel(
    *,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    rows: list[dict[str, Any]],
    value_key: str,
    max_abs_value: float,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    small_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    positive_color: str,
    negative_color: str,
    suffix: str,
) -> None:
    chart = (box[0] + 50, box[1] + 90, box[2] - 30, box[3] - 70)
    _draw_y_axis(
        draw=draw,
        chart=chart,
        max_value=max_abs_value,
        font=small_font,
        min_value=-max_abs_value,
    )

    zero_y = _scale_y(value=0.0, min_value=-max_abs_value, max_value=max_abs_value, chart=chart)
    draw.line((chart[0], zero_y, chart[2], zero_y), fill=_COLORS["axis"], width=2)
    group_width = (chart[2] - chart[0]) / max(len(rows), 1)
    bar_width = group_width * 0.35
    for index, row in enumerate(rows):
        center_x = chart[0] + group_width * (index + 0.5)
        value = float(row[value_key])
        y = _scale_y(value=value, min_value=-max_abs_value, max_value=max_abs_value, chart=chart)
        fill = positive_color if value >= 0 else negative_color
        draw.rounded_rectangle(
            (center_x - bar_width / 2, min(y, zero_y), center_x + bar_width / 2, max(y, zero_y)),
            radius=8,
            fill=fill,
        )
        label = row["workload_family"].replace("-prefix", "").replace("-", "\n")
        _draw_multiline_centered(
            draw=draw,
            xy=(center_x, chart[3] + 10),
            text=label,
            fill=_COLORS["text"],
            font=small_font,
        )
        draw.text(
            (center_x - 22, y - 18 if value >= 0 else y + 6),
            f"{value:.3f}{suffix}",
            fill=_COLORS["muted"],
            font=small_font,
        )


def _draw_line_panel(
    *,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    capacities: list[int],
    panel: dict[str, Any],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    small_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    chart = (box[0] + 50, box[1] + 90, box[2] - 25, box[3] - 55)
    _draw_y_axis(draw=draw, chart=chart, max_value=1.0, font=small_font, min_value=0.0)

    x_positions = {
        capacity: chart[0] + (chart[2] - chart[0]) * (index / max(len(capacities) - 1, 1))
        for index, capacity in enumerate(capacities)
    }
    for capacity, x in x_positions.items():
        draw.line((x, chart[3], x, chart[3] + 6), fill=_COLORS["axis"], width=1)
        label = str(capacity)
        bbox = draw.textbbox((0, 0), label, font=small_font)
        draw.text((x - (bbox[2] - bbox[0]) / 2, chart[3] + 10), label, fill=_COLORS["muted"], font=small_font)

    for policy_name, color in (("fifo", _COLORS["fifo"]), ("lru", _COLORS["lru"]), ("lfu", _COLORS["lfu"])):
        points = [
            (
                x_positions[capacity],
                _scale_y(value=float(value), min_value=0.0, max_value=1.0, chart=chart),
            )
            for capacity, value in zip(capacities, panel[policy_name], strict=True)
        ]
        draw.line(points, fill=color, width=4, joint="curve")
        for x, y in points:
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color)


def _draw_y_axis(
    *,
    draw: ImageDraw.ImageDraw,
    chart: tuple[int, int, int, int],
    max_value: float,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    min_value: float,
) -> None:
    ticks = 4
    draw.line((chart[0], chart[1], chart[0], chart[3]), fill=_COLORS["axis"], width=2)
    draw.line((chart[0], chart[3], chart[2], chart[3]), fill=_COLORS["axis"], width=2)
    for index in range(ticks + 1):
        fraction = index / ticks
        value = max_value - (max_value - min_value) * fraction
        y = chart[1] + (chart[3] - chart[1]) * fraction
        draw.line((chart[0], y, chart[2], y), fill=_COLORS["grid"], width=1)
        label = f"{value:.2f}".rstrip("0").rstrip(".")
        bbox = draw.textbbox((0, 0), label, font=font)
        draw.text((chart[0] - (bbox[2] - bbox[0]) - 10, y - 8), label, fill=_COLORS["muted"], font=font)


def _draw_value_bar(
    *,
    draw: ImageDraw.ImageDraw,
    chart: tuple[int, int, int, int],
    center_x: int,
    bar_width: int,
    value: float,
    max_value: float,
    color: str,
) -> None:
    bar_top = _scale_y(value=value, min_value=0.0, max_value=max_value, chart=chart)
    draw.rounded_rectangle(
        (center_x - bar_width / 2, bar_top, center_x + bar_width / 2, chart[3]),
        radius=8,
        fill=color,
    )


def _draw_panel_legend(
    *,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    items: list[tuple[str, str]],
    anchor: tuple[int, int],
) -> None:
    x, y = anchor
    for label, color in items:
        draw.rounded_rectangle((x, y + 4, x + 18, y + 18), radius=4, fill=color)
        draw.text((x + 26, y), label, fill=_COLORS["muted"], font=font)
        x += 90


def _draw_policy_legend(
    *,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    anchor: tuple[int, int],
) -> None:
    _draw_panel_legend(
        draw=draw,
        font=font,
        anchor=anchor,
        items=[
            ("FIFO", _COLORS["fifo"]),
            ("LRU", _COLORS["lru"]),
            ("LFU", _COLORS["lfu"]),
        ],
    )


def _draw_footer(
    *,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    report_slug: str,
    run_ids: list[str],
    y: int,
) -> None:
    footer = f"Source: {report_slug} | Runs: {', '.join(run_ids)}"
    draw.text((60, y), footer[:180], fill=_COLORS["muted"], font=font)


def _draw_multiline_centered(
    *,
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    fill: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    lines = text.splitlines()
    line_height = 16
    for index, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        width = bbox[2] - bbox[0]
        draw.text((xy[0] - width / 2, xy[1] + index * line_height), line, fill=fill, font=font)


def _scale_y(
    *,
    value: float,
    min_value: float,
    max_value: float,
    chart: tuple[int, int, int, int],
) -> float:
    if max_value == min_value:
        return float(chart[3])
    fraction = (value - min_value) / (max_value - min_value)
    return chart[3] - (chart[3] - chart[1]) * fraction
