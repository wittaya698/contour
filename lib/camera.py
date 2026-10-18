"""A span read through the camera, recovered from the picture (ADR 0032).

The old reading was one scale per reference: the anchor's millimetres over
its pixels. That holds where the picture is straight on and every span is as
far from the camera as the anchor. Here each traced **direction** is a set of
lines along edges parallel in the object; where they meet is how the camera
saw that direction, and three square to each other give the lens. The anchor,
placed through that camera, gives two points in the room; a span tied to one
of them is read from it along its own direction.

Every position is worked in the picture's own measure: pixels from its
centre, over its diagonal, so the arithmetic sees numbers near one whatever
the picture's size. The centre is taken for the lens's (ADR 0032,
consequences): a cropped picture reads off by however far it is not.

Standard library only: this is the Blender-free half, and the numbers have to
be checkable without a scene.
"""
import math

SAME = 2.0
"""Pixels within which two ends are one point: a corner clicked twice."""

LENSES = (0.5, 1.0, 2.0, 4.0, 8.0)
"""Focal lengths, in diagonals, tried when the directions do not give the
lens: wider than a phone's widest to a long zoom."""

AIM = math.radians(2)
"""How far a span's line may point off a direction's meeting point and still
run along it: a diagonal on a box's face is twenty degrees and more off."""

HOLDS = 0.01
"""How far a reading may move across `LENSES` and still not depend on the
lens: a span the camera cannot scale moves by its own size."""


def read(size, directions, anchor, spans):
    """`{span id: reading}`, each `{"mm", "tol", "along"}` or `{"why"}`.

    `size` is the picture's `(width, height)` in pixels. `directions` maps a
    name to its lines, each two pixels, and are taken as square to each other.
    `anchor` is `{"ends": (a, b), "mm": real length}`. `spans` maps an id to
    `{"ends": (p, q)}`, with `"on": (one direction, another)` for a span that
    lies on the plane those two span through the anchor's first end: where the
    anchor runs along either, the plane holds both its ends.
    """
    picture = Picture(size, directions, anchor, spans)
    plan = picture.plan()
    got = {}
    for name, step in plan.items():
        if "why" in step:
            got[name] = {"why": step["why"]}
            continue
        why = picture.unscaled(plan, name)
        if why:
            got[name] = {"why": why}
            continue
        mm = picture.measure(plan, name)
        got[name] = {"mm": mm, "tol": picture.bar(plan, name, mm), "along": step["along"]}
    return got


class Picture:
    """One reference's traced points, in the picture's own measure."""

    def __init__(self, size, directions, anchor, spans):
        self.centre = (size[0] / 2, size[1] / 2)
        self.scale = math.hypot(*size)
        # Every point the reading rests on, by a key, so the bar can move each.
        self.points = {}
        self.directions = {}
        for name, traced in directions.items():
            keys = []
            for n, (p, q) in enumerate(traced):
                keys.append((self._point(("line", name, n, 0), p),
                             self._point(("line", name, n, 1), q)))
            self.directions[name] = keys
        self.anchor = (self._point(("anchor", 0), anchor["ends"][0]),
                       self._point(("anchor", 1), anchor["ends"][1]))
        self.mm = float(anchor["mm"])
        self.spans = {name: (self._point(("span", name, 0), s["ends"][0]),
                             self._point(("span", name, 1), s["ends"][1]))
                      for name, s in spans.items()}
        self.on = {name: tuple(s["on"]) for name, s in spans.items() if s.get("on")}

    def _point(self, key, pixel):
        self.points[key] = ((pixel[0] - self.centre[0]) / self.scale,
                            (pixel[1] - self.centre[1]) / self.scale)
        return key

    def pixel(self, key):
        x, y = self.points[key]
        return (x * self.scale + self.centre[0], y * self.scale + self.centre[1])

    # -- what is read from what: decided once, on the points as traced -------

    def plan(self):
        """For each span: the direction it runs along and the end it is tied
        by, or why it is not read. Decided once, so moving a point a pixel for
        the bar moves the numbers and never the reasoning."""
        self.anchor_along = self.along(*self.anchor)
        if self.anchor_along is None:
            return {name: {"why": (
                f"the anchor runs along none of {_names(self.directions)}, so "
                f"it places nothing in the room and scales no span: a span "
                f"along one of them, of a length you know, would anchor them")}
                for name in self.spans}
        plan = {}
        waiting = {}
        for name, (p, q) in self.spans.items():
            along = self.along(p, q)
            if along is None:
                plan[name] = {"why": (
                    f"{name} runs along none of {_names(self.directions)}: a "
                    f"diagonal gives no number, and needs a direction of its "
                    f"own, traced along edges parallel to it")}
            elif name in self.on and along not in self.on[name]:
                plan[name] = {"why": (
                    f"{name} runs along {along}, which does not lie on the "
                    f"plane of {_names(self.on[name])} it is said to be on")}
            else:
                waiting[name] = along
        # In rounds: a span tied to one read this round is read the next.
        placed = list(self.anchor)
        while True:
            tied = {}
            for name, along in waiting.items():
                p, q = self.spans[name]
                for end, other in ((p, q), (q, p)):
                    at = next((k for k in placed
                               if math.dist(self.pixel(k), self.pixel(end)) <= SAME), None)
                    if at is not None:
                        tied[name] = {"along": along, "tied": at, "start": end, "finish": other}
                        break
                else:
                    if name in self.on:
                        tied[name] = {"along": along, "plane": self.on[name], "start": p, "finish": q}
            if not tied:
                break
            for name, step in tied.items():
                plan[name] = step
                placed += [step["start"], step["finish"]]
                del waiting[name]
        for name in waiting:
            plan[name] = {"why": (
                f"{name} is tied to nothing: the picture alone does not say "
                f"how far it is from the camera, and a length shrinks with "
                f"distance. An end shared with the anchor or a span already "
                f"read would tie it, or its lying on the plane through the "
                f"anchor that two of {_names(self.directions)} span")}
        return plan

    def along(self, p, q):
        """The direction a span runs along: the one whose meeting point its
        line points at, within a pixel at each end or `AIM`, whichever is
        wider. None when it points at none of them."""
        a, b = self.points[p], self.points[q]
        slack = max(AIM, math.atan2(2, math.dist(a, b) * self.scale))
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        best, angle = None, None
        for name in self.directions:
            v = self.vanishing(name)
            toward = (v[0] - v[2] * mid[0], v[1] - v[2] * mid[1])
            off = _angle((b[0] - a[0], b[1] - a[1]), toward)
            if off <= slack and (angle is None or off < angle):
                best, angle = name, off
        return best

    # -- the numbers ----------------------------------------------------------

    def vanishing(self, name):
        """Where a direction's lines meet, homogeneous: `(x, y, w)`, `w` near
        nought for lines parallel in the picture."""
        found = [_unit(_line(self.points[p], self.points[q])) for p, q in self.directions[name]]
        return _nearest(found)

    def lens(self):
        """The focal length in diagonals, or None when the directions do not
        give it: fewer than three, or none receding in a pair."""
        if len(self.directions) < 3:
            return None
        # Square directions through a lens `f` meet where
        # (x1 x2 + y1 y2) / f^2 + w1 w2 = 0, for each pair: one unknown, 1/f^2,
        # by least squares over the pairs. A pair parallel in the picture says
        # nothing, and adds nothing.
        vs = [_unit(self.vanishing(n)) for n in self.directions]
        top = bottom = 0.0
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                a = vs[i][0] * vs[j][0] + vs[i][1] * vs[j][1]
                b = vs[i][2] * vs[j][2]
                top -= a * b
                bottom += a * a
        if bottom < 1e-12 or top <= 0:
            return None
        return math.sqrt(bottom / top)

    def unscaled(self, plan, name):
        """Why the camera cannot scale this span, or None when it can.

        Where the directions do not give the lens, the span is read at every
        lens in `LENSES`. One along the picture's face reads the same at all
        of them, and is read; one into its depth does not, and the number
        would be whichever lens was guessed.
        """
        if self.lens() is not None:
            return None
        readings = [self.measure(plan, name, f) for f in LENSES]
        if max(readings) - min(readings) <= HOLDS * min(readings):
            return None
        along = plan[name]["along"]
        if len(self.directions) < 3:
            return (f"{name} runs along {along}, and its length depends on the "
                    f"lens, which {_names(self.directions)} alone do not give: "
                    f"it needs a third direction square to "
                    f"{_names(self.directions)}")
        return (f"{name} runs along {along}, and its length depends on the "
                f"lens, which this picture does not give: it is straight on, "
                f"and the lens needs two directions that both recede")

    def measure(self, plan, name, f=None):
        """A span's millimetres, through the lens the directions give, or
        `f`. Where they give none, `unscaled` has found that any will do."""
        f = f or self.lens() or LENSES[len(LENSES) // 2]
        return abs(self._placed(plan, f)[name])

    def _placed(self, plan, f):
        """Every span's length along its direction, at focal length `f`."""
        def ray(key):
            x, y = self.points[key]
            return (x / f, y / f, 1.0)

        def heading(name):
            v = self.vanishing(name)
            return _unit((v[0] / f, v[1] / f, v[2]))

        a, b = self.anchor
        s, t = _solve(ray(a), [-c for c in ray(b)],
                      [-self.mm * c for c in heading(self.anchor_along)])
        where = {a: [s * c for c in ray(a)], b: [t * c for c in ray(b)]}
        got = {}
        for name, step in plan.items():
            if "start" not in step:
                continue
            if "plane" in step:
                normal = _cross(*(heading(n) for n in step["plane"]))
                through = where[self.anchor[0]]
                r = ray(step["start"])
                start = [_dot(normal, through) / _dot(normal, r) * c for c in r]
            else:
                depth = where[step["tied"]][2]
                start = [depth * c for c in ray(step["start"])]
            along = heading(step["along"])
            mu, _ = _solve(along, [-c for c in ray(step["finish"])], [-c for c in start])
            where[step["start"]] = start
            where[step["finish"]] = [o + mu * d for o, d in zip(start, along)]
            got[name] = mu
        return got

    def bar(self, plan, name, mm):
        """The `±`: every point moved a pixel each way, the span read again.

        An end is one measurement, so each end's wider side is added, as the
        old bar added a pixel at each end of the span. A direction's lines are
        not: four of them say one meeting point between them, and adding all
        eight ends would count that one uncertainty eight times. A direction
        adds its widest single point instead.
        """
        step = 1 / self.scale
        moved = {}
        for key, (x, y) in list(self.points.items()):
            worst = 0.0
            for dx, dy in ((step, 0), (-step, 0), (0, step), (0, -step)):
                self.points[key] = (x + dx, y + dy)
                worst = max(worst, abs(self.measure(plan, name) - mm))
            self.points[key] = (x, y)
            owner = key[:2] if key[0] == "line" else key
            moved[owner] = max(moved.get(owner, 0.0), worst)
        return sum(moved.values())


def _names(directions):
    """`x, y and z`: the directions, as a sentence lists them."""
    names = list(directions)
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _cross(u, v):
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def _line(p, q):
    return (p[1] - q[1], q[0] - p[0], p[0] * q[1] - q[0] * p[1])


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def _angle(u, v):
    """The angle between two lines' headings, either way along each."""
    cos = abs(u[0] * v[0] + u[1] * v[1]) / (math.hypot(*u) * math.hypot(*v))
    return math.acos(min(1.0, cos))


def _nearest(lines):
    """The point nearest every line: the smallest eigenvector of the sum of
    their outer products, by Jacobi rotations."""
    m = [[sum(l[i] * l[j] for l in lines) for j in range(3)] for i in range(3)]
    vectors = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
    for _ in range(50):
        p, q = max(((0, 1), (0, 2), (1, 2)), key=lambda ij: abs(m[ij[0]][ij[1]]))
        if abs(m[p][q]) < 1e-15:
            break
        theta = (m[q][q] - m[p][p]) / (2 * m[p][q])
        t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1))
        c = 1 / math.sqrt(t * t + 1)
        s = t * c
        for k in range(3):
            mkp, mkq = m[k][p], m[k][q]
            m[k][p], m[k][q] = c * mkp - s * mkq, s * mkp + c * mkq
        for k in range(3):
            mpk, mqk = m[p][k], m[q][k]
            m[p][k], m[q][k] = c * mpk - s * mqk, s * mpk + c * mqk
        for k in range(3):
            vkp, vkq = vectors[k][p], vectors[k][q]
            vectors[k][p], vectors[k][q] = c * vkp - s * vkq, s * vkp + c * vkq
    smallest = min(range(3), key=lambda i: m[i][i])
    return tuple(vectors[k][smallest] for k in range(3))


def _solve(u, v, w):
    """`(a, b)` making `a * u + b * v` nearest `w`, by least squares."""
    uu = sum(x * x for x in u)
    vv = sum(x * x for x in v)
    uv = sum(x * y for x, y in zip(u, v))
    uw = sum(x * y for x, y in zip(u, w))
    vw = sum(x * y for x, y in zip(v, w))
    det = uu * vv - uv * uv
    return (uw * vv - vw * uv) / det, (vw * uu - uw * uv) / det
