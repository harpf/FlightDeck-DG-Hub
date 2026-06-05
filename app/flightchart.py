"""Server-side, dependency-free flight-path chart for a disc's flight numbers.

Renders the conventional top-down disc-golf trajectory (release at the bottom,
distance upward) as inline SVG, derived from Turn and Fade for a right-hand
backhand throw:

* ``turn`` (negative = high-speed turn right) -> a transient rightward bulge.
* ``fade``  (positive = low-speed finish left)  -> a late leftward pull, so an
  overstable disc lands left of centre.

It is an illustrative flight-rating chart, not an aerodynamic simulation.
"""
from __future__ import annotations

import math

from markupsafe import Markup, escape

WIDTH = 240
HEIGHT = 300
MARGIN = 24
AMP_TURN = 12.0  # px of rightward bulge per point of (−)turn
AMP_FADE = 13.0  # px of leftward finish per point of fade


def flight_path_points(
    turn: int | None,
    fade: int | None,
    *,
    width: int = WIDTH,
    height: int = HEIGHT,
    n: int = 24,
) -> list[tuple[float, float]]:
    """Top-down trajectory points from release (bottom) to landing (top)."""
    turn_value = turn or 0
    fade_value = fade or 0
    center = width / 2
    top = MARGIN
    bottom = height - MARGIN
    points: list[tuple[float, float]] = []
    for i in range(n + 1):
        t = i / n
        y = bottom - t * (bottom - top)
        # Turn: rightward bulge, zero at release and landing.
        turn_component = AMP_TURN * (-turn_value) * math.sin(math.pi * t)
        # Fade: ramps in after mid-flight, fully applied at landing.
        ramp = max(0.0, (t - 0.45) / 0.55)
        fade_component = AMP_FADE * fade_value * (ramp ** 2)
        x = center + turn_component - fade_component
        x = min(max(x, 0.0), float(width))
        points.append((x, y))
    return points


def _fmt(value: int | None) -> str:
    return "–" if value is None else str(value)


def render_flight_svg(
    speed: int | None,
    glide: int | None,
    turn: int | None,
    fade: int | None,
    *,
    width: int = WIDTH,
    height: int = HEIGHT,
) -> Markup | None:
    """Inline SVG flight chart, or ``None`` when no flight numbers are known."""
    if speed is None and glide is None and turn is None and fade is None:
        return None

    points = flight_path_points(turn, fade, width=width, height=height)
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    center = width / 2
    start_x, start_y = points[0]
    end_x, end_y = points[-1]
    # Escape the caption defensively: values should already be ints, but never emit
    # unescaped data into this raw-Markup SVG (text node + aria-label attribute).
    caption = escape(f"S {_fmt(speed)} · G {_fmt(glide)} · T {_fmt(turn)} · F {_fmt(fade)}")

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" '
        f'aria-label="Flugkurve {caption}" class="flight-chart">'
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="10" '
        f'fill="#f8faf8" stroke="#d8e0d8"/>'
        f'<line x1="{center}" y1="{MARGIN}" x2="{center}" y2="{height - MARGIN}" '
        f'stroke="#cdd6cd" stroke-width="1" stroke-dasharray="4 4"/>'
        f'<polyline points="{polyline}" fill="none" stroke="#2e7d32" '
        f'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{start_x:.1f}" cy="{start_y:.1f}" r="4" fill="#2e7d32"/>'
        f'<circle cx="{end_x:.1f}" cy="{end_y:.1f}" r="4" fill="#c62828"/>'
        f'<text x="{center}" y="{height - 7}" text-anchor="middle" '
        f'font-size="12" fill="#5a665a">{caption}</text>'
        f'</svg>'
    )
    return Markup(svg)
