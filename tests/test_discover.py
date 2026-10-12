import pytest

from nikon2jpeg.discover import DiscoverError, output_dir_for, plan


def _touch(p):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")
    return p


def test_folder_goes_to_sibling(tmp_path):
    trip = tmp_path / "Trip"
    _touch(trip / "DSC_1.NEF")
    _touch(trip / "DSC_2.nef")
    _touch(trip / "notes.txt")
    jobs = plan([trip])
    assert sorted(j.dst.name for j in jobs) == ["DSC_1.jpg", "DSC_2.jpg"]
    assert all(j.dst.parent == tmp_path / "Trip_jpeg" for j in jobs)


def test_single_file_and_dedup(tmp_path):
    f = _touch(tmp_path / "Trip" / "DSC_1.NEF")
    jobs = plan([f, tmp_path / "Trip"])
    assert len(jobs) == 1
    assert jobs[0].dst == tmp_path / "Trip_jpeg" / "DSC_1.jpg"


def test_recursive_mirrors_subtree(tmp_path):
    _touch(tmp_path / "Trip" / "Day2" / "a.nef")
    assert plan([tmp_path / "Trip"]) == []
    (job,) = plan([tmp_path / "Trip"], recursive=True)
    assert job.dst == tmp_path / "Trip_jpeg" / "Day2" / "a.jpg"


def test_non_ascii_and_spaces(tmp_path):
    f = _touch(tmp_path / "Férias 2026" / "a.nef")
    (job,) = plan([f])
    assert job.dst.parent.name == "Férias 2026_jpeg"


def test_output_folder_rejected(tmp_path):
    out = tmp_path / "Trip_jpeg"
    out.mkdir()
    with pytest.raises(DiscoverError):
        output_dir_for(out)


def test_rejects_other_files(tmp_path):
    with pytest.raises(DiscoverError):
        plan([_touch(tmp_path / "a.jpg")])
