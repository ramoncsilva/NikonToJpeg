from pathlib import Path

import pytest
from PIL import Image

from nikon2jpeg import pipeline
from nikon2jpeg.config import Settings
from nikon2jpeg.discover import plan

NEF = Path(__file__).parent / "data" / "_DSC0071.NEF"
pytestmark = pytest.mark.skipif(not NEF.exists(), reason="local NEF fixture not present")


def test_convert_real_nef(tmp_path):
    src = tmp_path / "shoot" / NEF.name
    src.parent.mkdir()
    src.write_bytes(NEF.read_bytes())
    (job,) = plan([src.parent])
    result = pipeline.convert_one(job, Settings())
    assert result.status == "converted", result.detail
    assert job.dst.parent.name == "shoot_jpeg"
    with Image.open(job.dst) as im:
        assert max(im.size) == 2048
        assert im.info.get("icc_profile")
        assert "GPSInfo" not in {k for k in im.getexif().get_ifd(0x8825)} or not im.getexif().get_ifd(0x8825)
    assert src.read_bytes() == NEF.read_bytes()  # original untouched
