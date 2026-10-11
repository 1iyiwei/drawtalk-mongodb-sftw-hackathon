from app import scenes

PROG = {"type": "move_along", "path": "default", "speed": 100, "duration": None, "arc_height": None, "easing": "linear"}


def test_resimulate_follows_new_start_and_target():
    ents = {"r": {"bbox": [-10, -10, 10, 10]}, "t": {"bbox": [-20, -50, 20, 50]}}
    beh = {("run", 1): {"program": PROG}}
    clip = {"clip_id": "c", "actor": "r", "target": "t", "behavior_id": "run", "behavior_version": 1, "params": {},
            "path": {"kind": "default", "points": [[0, 0], [270, 0]]}, "start": 0, "duration": 2.7,
            "end_state": {"x": 270, "y": 0}, "frames": [[0, 0, 0, 1, 1, 1]]}
    start = {"r": {"x": 100, "y": 0}, "t": {"x": 300, "y": 0}}
    out = scenes.resimulate([clip], start, ents, beh)
    assert abs(out[0]["end_state"]["x"] - 270) < 1 and abs(out[0]["duration"] - 1.7) < 0.05


def test_resimulate_drops_clips_of_removed_characters():
    out = scenes.resimulate([{"clip_id": "c", "actor": "gone", "start": 0, "duration": 1}], {}, {}, {})
    assert out == []
