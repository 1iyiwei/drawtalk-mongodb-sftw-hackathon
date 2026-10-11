from app import refine

V1 = {"program": {"type": "layer", "base": {"type": "move_along", "path": "default", "speed": {"param": "speed"},
                                           "duration": None, "arc_height": None, "easing": "linear"},
                  "mods": [{"type": "bob", "amplitude": 3, "period": 0.8}]},
      "params": [{"name": "speed", "unit": "px/s", "default": 60, "min": 20, "max": 200, "cues": []}]}


def test_diff_is_readable():
    v2 = {"program": {**V1["program"], "mods": [{"type": "bob", "amplitude": 1.5, "period": 0.8}]},
          "params": [{**V1["params"][0], "default": 90}]}
    lines = refine.diff(V1, v2)
    assert "program.mods[bob].amplitude: 3 → 1.5" in lines
    assert "params.speed.default: 60 → 90" in lines


def test_retime_keeps_groups_and_order():
    tl = [{"start": 0, "duration": 2}, {"start": 0, "duration": 5}, {"start": 5, "duration": 1}]
    tl[1]["duration"] = 3  # the longer clip of the first group got faster
    out = refine.retime(tl)
    assert [c["start"] for c in out] == [0, 0, 3]


def test_replay_keeps_end_position_for_speed_change():
    clip = {"frames": [[0, 0, 0, 1, 1, 1]], "path": {"kind": "default", "points": [[0, 0], [300, 0]]},
            "params": {"speed": 60}, "end_state": {"x": 300, "y": 0}, "duration": 5.0}
    v2 = {**V1, "params": [{**V1["params"][0], "default": 120}]}
    new = refine.replay_clip(clip, v2, {"speed": 120})
    res = refine.compare(clip, new)
    assert res["pass"] and res["duration_after"] < res["duration_before"]


def test_scaled_overrides_follow_default_ratio():
    clip = {"params": {"speed": 55}}
    new = [{**V1["params"][0], "default": 120}]
    assert refine.scaled_overrides(clip, V1["params"], new) == {"speed": 110}
