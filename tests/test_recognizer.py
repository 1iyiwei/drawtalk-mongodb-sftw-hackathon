import math

from app import recognizer as r


def arc(x0, y0, w, h, n=40):
    return [(x0 + w * i / n, y0 - h * math.sin(math.pi * i / n)) for i in range(n + 1)]


def zigzag(x0, y0, w, h, n=6):
    return [(x0 + w * i / n, y0 + (h if i % 2 else 0)) for i in range(n + 1)]


def test_same_shape_different_size_and_place_matches():
    a = r.normalize(arc(0, 0, 300, 80))
    b = r.normalize(arc(500, 400, 150, 40))
    assert r.similarity(a, b) > 0.9


def test_different_shapes_score_lower():
    a = r.normalize(arc(0, 0, 300, 80))
    z = r.normalize(zigzag(0, 0, 300, 80))
    line = r.normalize([(0, 0), (300, 0)])
    assert r.similarity(a, z) < r.similarity(a, r.normalize(arc(10, 10, 280, 70)))
    assert r.similarity(a, line) < 0.9


def z(w, h):
    pts = [(0, 0), (w, 0), (0, h), (w, h)]
    return [(a + (c - a) * i / 10, b + (d - b) * i / 10) for (a, b), (c, d) in zip(pts, pts[1:]) for i in range(10)] + [pts[-1]]


def test_gesture_similarity_ignores_aspect_but_not_shape():
    base = r.normalize(z(50, 50))
    assert r.gesture_similarity(base, r.normalize(z(90, 30))) > 0.6
    circle = [(20 * math.cos(a / 10 * 6.28), 20 * math.sin(a / 10 * 6.28)) for a in range(11)]
    assert r.gesture_similarity(base, r.normalize(circle)) < 0.45
