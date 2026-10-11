"""2D geometry helpers: bounding boxes, default paths, polylines. Screen coordinates (px, y down)."""

import math

Point = tuple[float, float]


def bbox(points: list[Point]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def entity_world_bbox(entity: dict, state: dict) -> tuple[float, float, float, float]:
    """Local bbox (around the pivot at 0,0) placed at the instance position and scale. Rotation ignored."""
    x0, y0, x1, y1 = entity["bbox"]
    sx, sy = abs(state.get("sx", 1)), abs(state.get("sy", 1))
    return state["x"] + x0 * sx, state["y"] + y0 * sy, state["x"] + x1 * sx, state["y"] + y1 * sy


def contains(b, p: Point, pad: float = 0) -> bool:
    return b[0] - pad <= p[0] <= b[2] + pad and b[1] - pad <= p[1] <= b[3] + pad


def polyline_length(pts: list[Point]) -> float:
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def point_at(pts: list[Point], u: float) -> Point:
    """Point at fraction u (0..1) of arc length along a polyline."""
    if len(pts) == 1:
        return pts[0]
    total = polyline_length(pts)
    if total == 0:
        return pts[0]
    target = max(0.0, min(1.0, u)) * total
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = math.dist(a, b)
        if acc + seg >= target and seg > 0:
            f = (target - acc) / seg
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        acc += seg
    return pts[-1]


def ray_box_exit(origin: Point, target: Point, box) -> Point:
    """Where the segment origin→target first enters `box` (the box contains target). Falls back to target."""
    ox, oy = origin
    dx, dy = target[0] - ox, target[1] - oy
    best = 1.0
    for t in _slab_hits(ox, dx, box[0], box[2]) + _slab_hits(oy, dy, box[1], box[3]):
        if 0 <= t <= 1:
            px, py = ox + dx * t, oy + dy * t
            if contains(box, (px, py), pad=0.5):
                best = min(best, t)
    return ox + dx * best, oy + dy * best


def _slab_hits(o, d, lo, hi):
    if abs(d) < 1e-9:
        return []
    return [(lo - o) / d, (hi - o) / d]


def default_path(actor_state: dict, actor: dict, target_box) -> list[Point]:
    """Straight line from the actor center to where the actor touches the target's bbox (stop on contact)."""
    start = (actor_state["x"], actor_state["y"])
    tc = ((target_box[0] + target_box[2]) / 2, (target_box[1] + target_box[3]) / 2)
    hit = ray_box_exit(start, tc, target_box)
    # back off by the actor's half-extent along the direction of travel so the edges just touch
    ax0, ay0, ax1, ay1 = actor["bbox"]
    dx, dy = hit[0] - start[0], hit[1] - start[1]
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return [start, start]
    ux, uy = dx / dist, dy / dist
    half = abs(ux) * (ax1 - ax0) / 2 + abs(uy) * (ay1 - ay0) / 2
    end_d = max(0.0, dist - half)
    return [start, (start[0] + ux * end_d, start[1] + uy * end_d)]


def arc_path(straight: list[Point], height: float, n: int = 24) -> list[Point]:
    (x0, y0), (x1, y1) = straight[0], straight[-1]
    return [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n - height * math.sin(math.pi * i / n)) for i in range(n + 1)]


def stroke_path(actor_state: dict, stroke_pts: list[Point]) -> list[Point]:
    """Use the drawn stroke as the path, shifted so it starts at the actor (no jump)."""
    ox, oy = stroke_pts[0][0] - actor_state["x"], stroke_pts[0][1] - actor_state["y"]
    return [(x - ox, y - oy) for x, y in stroke_pts]


CANVAS = (0.0, 0.0, 1000.0, 600.0)


def direction_path(actor_state: dict, actor: dict, direction: str, distance: float) -> list[Point]:
    """Straight move in a screen direction, clamped so the actor stays inside the canvas."""
    dx, dy = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}[direction]
    x0, y0, x1, y1 = actor["bbox"]
    sx, sy = actor_state["x"], actor_state["y"]
    ex = min(max(sx + dx * distance, CANVAS[0] - x0), CANVAS[2] - x1)
    ey = min(max(sy + dy * distance, CANVAS[1] - y0), CANVAS[3] - y1)
    return [(sx, sy), (ex, ey)]
