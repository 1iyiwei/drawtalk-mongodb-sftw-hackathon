from app import dsl, geometry


def ctx(**params):
    return dsl.Ctx(params=params, path_default=[(0.0, 0.0), (300.0, 0.0)])


DASH = {
    "type": "layer",
    "base": {"type": "move_along", "path": "default", "speed": {"param": "speed"}, "duration": None, "arc_height": None, "easing": "linear"},
    "mods": [{"type": "hop", "height": 30, "every_px": 60, "squash": 0.2}, {"type": "face_motion"}],
}


def test_move_duration_follows_speed():
    out = dsl.run(DASH, {"x": 0, "y": 0}, ctx(speed=300))
    assert abs(out["duration"] - 1.0) < 0.05
    assert abs(out["end_state"]["x"] - 300) < 1


def test_hop_lifts_mid_hop_and_lands():
    out = dsl.run(DASH, {"x": 0, "y": 0}, ctx(speed=300))
    ys = [f[1] for f in out["frames"]]
    assert min(ys) < -20  # up is negative y
    assert abs(ys[-1]) < 1  # 300 px / 60 px per hop → lands at the end


def test_face_motion_flips_when_moving_left():
    c = dsl.Ctx(params={"speed": 300}, path_default=[(300.0, 0.0), (0.0, 0.0)])
    out = dsl.run(DASH, {"x": 300, "y": 0}, c)
    assert out["frames"][-1][3] < 0


def test_seq_nap_emits_glyphs_and_rotates():
    nap = {
        "type": "seq",
        "steps": [
            {"type": "turn_to", "angle": 80, "duration": 0.5, "easing": "easeInOut"},
            {"type": "layer", "base": {"type": "stay", "duration": 2},
             "mods": [{"type": "emit", "glyph": "Z", "every": 0.8, "rise": 40, "fade": 1.2}]},
        ],
    }
    out = dsl.run(nap, {"x": 10, "y": 10}, ctx())
    assert out["end_state"]["rot"] == 80
    assert len(out["events"]) == 3 and out["events"][0]["t"] >= 0.5


def test_validate_rejects_unknown_param():
    try:
        dsl.validate(DASH, set())
    except dsl.DSLError as e:
        assert "speed" in str(e)
    else:
        raise AssertionError("expected DSLError")


def test_clamp_records_reason():
    clamps = []
    p = dsl.resolve_params([{"name": "speed", "unit": "px/s", "default": 100, "min": 10, "max": 500, "cues": []}], {"speed": 9000}, clamps)
    assert p["speed"] == 500 and clamps


def test_default_path_stops_on_contact():
    actor = {"bbox": [-20, -20, 20, 20]}
    path = geometry.default_path({"x": 0, "y": 0}, actor, (200, -50, 300, 50))
    assert abs(path[-1][0] - 180) < 1e-6  # target edge at 200 minus actor half-width 20


def test_direction_path_stays_on_canvas():
    actor = {"bbox": [-20, -20, 20, 20]}
    path = geometry.direction_path({"x": 900, "y": 300}, actor, "right", 600)
    assert path[-1] == (980, 300)


def test_drawn_path_overrides_default_path():
    c = dsl.Ctx(params={"speed": 100}, path_default=None, path_stroke=[(0.0, 0.0), (0.0, 180.0)])
    out = dsl.run(DASH, {"x": 0, "y": 0}, c)
    assert abs(out["end_state"]["y"] - 180) < 1 and out["duration"] > 1.5


def test_rotate_by_is_relative_and_visible():
    spin = {"type": "rotate_by", "degrees": 360, "duration": 1, "easing": "linear"}
    out = dsl.run(spin, {"x": 0, "y": 0, "rot": 90}, ctx())
    assert out["end_state"]["rot"] == 450 and dsl.visible_change(out, {"x": 0, "y": 0})["visible"]


def test_one_degree_turn_is_not_visible():
    out = dsl.run({"type": "turn_to", "angle": 1, "duration": 2, "easing": "linear"}, {"x": 0, "y": 0}, ctx())
    assert not dsl.visible_change(out, {"x": 0, "y": 0})["visible"]


def test_gets_up_before_moving_when_lying_down():
    out = dsl.run(DASH, {"x": 0, "y": 0, "rot": 80}, ctx(speed=300))
    assert abs(out["end_state"]["rot"]) < 1 and out["frames"][0][2] == 80
