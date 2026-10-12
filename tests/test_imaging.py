import numpy as np
from PIL import Image

from nikon2jpeg import dust, encode
from nikon2jpeg.denoise import denoise


def _sky(w=2000, h=1000):
    rng = np.random.default_rng(0)
    img = np.full((h, w, 3), (120, 160, 220), np.uint8)
    return np.clip(img + rng.normal(0, 1.5, img.shape), 0, 255).astype(np.uint8)


def test_dust_spot_removed():
    img = _sky()
    yy, xx = np.ogrid[:1000, :2000]
    img[(yy - 300) ** 2 + (xx - 500) ** 2 <= 9] = (90, 125, 185)  # faint dark disc
    cleaned, mask = dust.remove_dust(img)
    assert mask[300, 500] == 255
    assert abs(int(cleaned[300, 500, 0]) - 120) < 10


def test_large_dark_object_preserved():
    img = _sky()
    img[300:420, 500:640] = (20, 20, 20)  # a building / bird, not dust
    cleaned, mask = dust.remove_dust(img)
    assert not mask[350:400, 520:620].any()
    assert (cleaned[350:400, 520:620] == 20).all()


def test_denoise_reduces_noise():
    rng = np.random.default_rng(1)
    flat = np.full((200, 200, 3), 128, np.uint8)
    noisy = np.clip(flat + rng.normal(0, 12, flat.shape), 0, 255).astype(np.uint8)
    assert denoise(noisy, "medium").std() < noisy.std()
    assert denoise(noisy, "off") is noisy


def test_resize_never_upscales():
    img = np.zeros((100, 200, 3), np.uint8)
    assert encode.resize(img, 2048).shape == img.shape
    assert encode.resize(img, 100).shape[:2] == (50, 100)


def test_write_jpeg_atomic_and_icc(tmp_path):
    dst = tmp_path / "out" / "a.jpg"
    encode.write_jpeg(_sky(300, 200), dst, 82, None)
    assert dst.exists() and not list(dst.parent.glob("*.tmp"))
    with Image.open(dst) as im:
        assert im.format == "JPEG" and im.info.get("icc_profile")
