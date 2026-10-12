import threading

import numpy as np

from nikon2jpeg import collect, dust, dustmap


def test_collect_merges_followers_into_leader():
    port, out = 47999, {}

    def leader():
        out["paths"] = collect.collect(["a"], port=port, window=0.5)

    t = threading.Thread(target=leader)
    t.start()
    import time

    time.sleep(0.2)
    assert collect.collect(["b"], port=port) is None
    assert collect.collect(["c", "d"], port=port) is None
    t.join()
    assert sorted(out["paths"]) == ["a", "b", "c", "d"]


def test_collect_alone_returns_own_paths():
    assert collect.collect(["x"], port=47998, window=0.1) == ["x"]


def _mask(*points):
    m = np.zeros((100, 200), np.uint8)
    for y, x in points:
        m[y, x] = 255
    return m


def test_consensus_keeps_only_recurring_spots():
    cands = [(0, _mask((50, 60), (10, 20 * i))) for i in range(5)]  # (50,60) recurs, other moves
    (found,) = dustmap.consensus(cands).values()
    assert found[50, 60] == 255
    assert found[10, 0] == 0


def test_consensus_needs_enough_frames_and_groups_by_orientation():
    assert dustmap.consensus([(0, _mask((5, 5)))] * 2) == {}
    mixed = [(0, _mask((5, 5)))] * 3 + [(6, _mask((9, 9)))] * 2
    assert set(dustmap.consensus(mixed)) == {0}


def test_shoot_map_repairs_spot_in_textured_frame():
    rng = np.random.default_rng(2)
    img = rng.integers(60, 200, (200, 400, 3), dtype=np.uint8)  # texture: own detector stays away
    shoot = np.zeros((200, 400), np.uint8)
    shoot[100, 200] = 255
    _, mask = dust.remove_dust(img, shoot_map=shoot)
    assert mask[100, 200] == 255
    assert not dust.detect(img).any()
