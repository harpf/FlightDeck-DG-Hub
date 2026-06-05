"""Tests for the server-side flight-path chart geometry and SVG."""
from app.flightchart import flight_path_points, render_flight_svg

WIDTH, HEIGHT = 240, 300


def _x_at_landing(points):
    # Points run release (bottom) -> landing (top); landing is the last point.
    return points[-1][0]


def test_straight_disc_stays_centered():
    points = flight_path_points(0, 0, width=WIDTH, height=HEIGHT, n=24)
    center = WIDTH / 2
    assert all(abs(x - center) < 1e-6 for x, _ in points)


def test_overstable_disc_lands_left_of_center():
    # turn 0, strong fade -> finishes left (smaller x).
    points = flight_path_points(0, 4, width=WIDTH, height=HEIGHT, n=24)
    assert _x_at_landing(points) < WIDTH / 2


def test_understable_disc_bulges_right():
    # negative turn -> a rightward (larger x) excursion mid-flight.
    points = flight_path_points(-3, 0, width=WIDTH, height=HEIGHT, n=24)
    max_x = max(x for x, _ in points)
    assert max_x > WIDTH / 2


def test_all_points_inside_box():
    points = flight_path_points(-5, 5, width=WIDTH, height=HEIGHT, n=24)
    assert all(0 <= x <= WIDTH and 0 <= y <= HEIGHT for x, y in points)


def test_render_flight_svg_none_without_numbers():
    assert render_flight_svg(None, None, None, None) is None


def test_render_flight_svg_returns_markup_with_numbers():
    svg = render_flight_svg(11, 5, -1, 3)
    assert svg is not None
    text = str(svg)
    assert text.startswith("<svg")
    assert "</svg>" in text
    assert "polyline" in text or "path" in text


def test_render_flight_svg_escapes_caption_values():
    # Defense in depth: even a string value must not break out of the SVG text/attr.
    svg = str(render_flight_svg("</text><script>alert(1)</script>", 5, -1, 3))
    assert "<script>" not in svg
    assert "&lt;/text&gt;" in svg or "&lt;script&gt;" in svg
