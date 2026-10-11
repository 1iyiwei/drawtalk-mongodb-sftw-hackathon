"""$P point-cloud gesture recognizer (Vatavu, Anthony, Wobbrock 2012), compact version.

Templates are resampled to N points, scaled uniformly and translated to the centroid. Direction is not
normalized away (a stroke drawn right-to-left differs from left-to-right only through endpoints; we keep the
point order out of $P and use start/end entities separately).
"""

import math

N = 32


def resample(pts: list[tuple[float, float]], n: int = N) -> list[tuple[float, float]]:
    pts = [tuple(p[:2]) for p in pts]
    if len(pts) < 2:
        return [pts[0]] * n if pts else [(0.0, 0.0)] * n
    total = sum(math.dist(pts[i - 1], pts[i]) for i in range(1, len(pts)))
    if total == 0:
        return [pts[0]] * n
    step, acc, out = total / (n - 1), 0.0, [pts[0]]
    src = list(pts)
    i = 1
    while i < len(src):
        d = math.dist(src[i - 1], src[i])
        if acc + d >= step and d > 0:
            t = (step - acc) / d
            q = (src[i - 1][0] + t * (src[i][0] - src[i - 1][0]), src[i - 1][1] + t * (src[i][1] - src[i - 1][1]))
            out.append(q)
            src.insert(i, q)
            acc = 0.0
        else:
            acc += d
        i += 1
    while len(out) < n:
        out.append(src[-1])
    return out[:n]


def normalize(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    pts = resample(pts)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    size = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    scaled = [((x - min(xs)) / size, (y - min(ys)) / size) for x, y in pts]
    cx, cy = sum(p[0] for p in scaled) / len(scaled), sum(p[1] for p in scaled) / len(scaled)
    return [(round(x - cx, 4), round(y - cy, 4)) for x, y in scaled]


def _cloud_distance(a, b, start: int) -> float:
    n = len(a)
    matched = [False] * n
    total, i = 0.0, start
    for k in range(n):
        best, idx = math.inf, -1
        for j in range(n):
            if not matched[j]:
                d = math.dist(a[i], b[j])
                if d < best:
                    best, idx = d, j
        matched[idx] = True
        weight = 1 - ((k - start + n) % n) / n
        total += weight * best
        i = (i + 1) % n
    return total


def distance(a, b) -> float:
    """$P greedy cloud match distance between two normalized templates (lower = more similar)."""
    n = len(a)
    step = max(1, int(n ** 0.5))
    return min(min(_cloud_distance(a, b, i), _cloud_distance(b, a, i)) for i in range(0, n, step))


def similarity(a, b) -> float:
    """Map $P distance to 0..1 (1 = identical). ~0.8+ is a confident match for 32-point templates."""
    return max(0.0, 1.0 - distance(a, b) / 5.0)
