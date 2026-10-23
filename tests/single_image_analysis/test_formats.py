"""Every file format scan() reads, and what it says about the files it does
not read: JPG/BMP, colour and RGBA, multi-page TIFF, float images, video."""
import dataclasses
import json
import os

import cv2
import numpy as np
import pytest

from dipesh import DetectionParams, analyse, detect, load_image, scan, to_float
from dipesh.single_image_analysis import (Item, close_videos, frame_range,
                                          load_item, loading, to_grey)

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "..", "reference")
with open(os.path.join(REF, "golden.json")) as f:
    GOLDEN = json.load(f)["frames"]


def frame_1():
    img = cv2.imread(os.path.join(REF, "images", "frame_1.tiff"),
                     cv2.IMREAD_UNCHANGED)
    assert img.dtype == np.uint8 and img.ndim == 2
    return img


def plain(v):
    return v.item() if hasattr(v, "item") else (
        [plain(x) for x in v] if isinstance(v, (list, tuple)) else v)


def assert_golden(path, name="frame_1.tiff"):
    """The image at path gives exactly the stored numbers of a reference
    frame: same count, same per-image numbers, same numbers for every spot."""
    spots, info = detect(to_float(load_image(path)), DetectionParams(),
                         photometry=True)
    want = GOLDEN[name]
    assert len(spots) == want["count"]
    assert {k: plain(v) for k, v in dataclasses.asdict(info).items()} \
        == want["info"]
    got = [{k: plain(v) for k, v in dataclasses.asdict(s).items()}
           for s in spots]
    assert got == want["spots"]


# ── A1: nothing is dropped silently ─────────────────────────────────────────

def test_files_that_are_not_read_are_reported_with_a_reason(tmp_path):
    cv2.imwrite(str(tmp_path / "a.png"), frame_1())
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "anim.gif").write_bytes(b"GIF89a")
    (tmp_path / "README").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "Thumbs.db").write_bytes(b"x")       # system file: not data
    (tmp_path / ".hidden").write_text("x")
    items = scan(str(tmp_path))
    assert [i.name for i in items] == ["a"]
    why = {os.path.basename(p): r for p, r in items.skipped}
    assert set(why) == {"notes.txt", "anim.gif", "README", "sub"}
    assert ".txt files are not read" in why["notes.txt"]
    assert ".gif files are not read" in why["anim.gif"]
    assert "no file extension" in why["README"]
    assert "subfolder" in why["sub"]


def test_a_single_unreadable_file_or_a_missing_path_is_reported(tmp_path):
    (tmp_path / "notes.txt").write_text("x")
    got = scan(str(tmp_path / "notes.txt"))
    assert got == [] and got.skipped[0].reason.startswith(".txt files")
    got = scan(str(tmp_path / "missing"))
    assert got == [] and got.skipped[0].reason == "not found"


def test_run_folders_report_images_they_do_not_use(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    a = runs / "pbar_run_1"
    a.mkdir()
    cv2.imwrite(str(a / "camera.tiff"), frame_1())
    cv2.imwrite(str(a / "preview.png"), frame_1())
    (a / "Batman.json").write_text("[]")            # metadata: not reported
    (a / "settings.xml").write_text("<x/>")         # metadata: not reported
    (runs / "pbar_run_2").mkdir()                   # no image at all
    (runs / "summary.png").write_bytes(b"")
    items = scan(str(runs))
    assert [i.path for i in items] == [str(a / "camera.tiff")]
    why = {os.path.basename(p): r for p, r in items.skipped}
    assert set(why) == {"preview.png", "pbar_run_2", "summary.png"}
    assert "uses camera.tiff" in why["preview.png"]
    assert "no image or video" in why["pbar_run_2"]
    assert "beside pbar_run_ folders" in why["summary.png"]


# ── A2: more formats, colour to grey ────────────────────────────────────────

@pytest.mark.parametrize("ext", [".png", ".bmp", ".tif"])
def test_lossless_copies_of_a_reference_frame_give_the_golden_numbers(
        tmp_path, ext):
    p = str(tmp_path / f"frame_1{ext}")
    assert cv2.imwrite(p, frame_1())
    assert [i.path for i in scan(str(tmp_path))] == [p]
    assert_golden(p)


def test_jpg_and_jpeg_files_are_read(tmp_path):
    img = frame_1()
    for name in ("a.jpg", "b.JPEG"):
        cv2.imwrite(str(tmp_path / name), img, [cv2.IMWRITE_JPEG_QUALITY, 98])
    items = scan(str(tmp_path))
    assert [i.name for i in items] == ["a", "b"]
    got = load_item(items[0])
    assert got.shape == img.shape and got.dtype == np.float32
    assert np.abs(got - img).mean() < 2.0             # JPEG is lossy


def test_run_folders_take_png_bmp_and_jpg_images(tmp_path):
    for k, ext in enumerate((".png", ".bmp", ".jpg")):
        d = tmp_path / f"pbar_run_{k}"
        d.mkdir()
        cv2.imwrite(str(d / f"camera{ext}"), frame_1())
    items = scan(str(tmp_path))
    assert [os.path.basename(i.path) for i in items] == [
        "camera.png", "camera.bmp", "camera.jpg"]


def test_a_tiff_is_still_preferred_in_a_run_folder(tmp_path):
    cv2.imwrite(str(tmp_path / "a.png"), frame_1())
    cv2.imwrite(str(tmp_path / "z.tiff"), frame_1())
    (tmp_path / "Batman.json").write_text("[]")
    assert os.path.basename(scan(str(tmp_path))[0].path) == "z.tiff"


def test_colour_becomes_grey_with_the_bt601_weights():
    rng = np.random.default_rng(1)
    bgr = rng.integers(0, 256, (16, 16, 3)).astype(np.uint8)
    b, g, r = (bgr[..., i].astype(np.float64) for i in range(3))
    want = (0.299 * r + 0.587 * g + 0.114 * b).astype(np.float32)
    assert np.array_equal(to_grey(bgr), want)


def test_a_grey_image_stored_as_colour_keeps_its_values_exactly():
    img = frame_1()
    assert np.array_equal(to_grey(cv2.merge([img, img, img])),
                          img.astype(np.float32))


def test_the_alpha_channel_is_dropped(tmp_path):
    rng = np.random.default_rng(2)
    bgr = rng.integers(0, 256, (16, 16, 3)).astype(np.uint8)
    alpha = rng.integers(0, 256, (16, 16)).astype(np.uint8)
    cv2.imwrite(str(tmp_path / "rgba.png"), cv2.merge([*cv2.split(bgr), alpha]))
    cv2.imwrite(str(tmp_path / "rgb.png"), bgr)
    assert np.array_equal(load_image(str(tmp_path / "rgba.png")),
                          load_image(str(tmp_path / "rgb.png")))
    grey = frame_1()
    cv2.imwrite(str(tmp_path / "ga.png"), cv2.merge([grey, grey, grey, grey]))
    assert np.array_equal(load_image(str(tmp_path / "ga.png")),
                          grey.astype(np.float32))


# ── A3: multi-page TIFF ─────────────────────────────────────────────────────

def pages(n):
    base = frame_1()
    return [np.roll(base, 37 * k, axis=1) for k in range(n)]


def test_each_page_of_a_tiff_is_one_item(tmp_path):
    p = str(tmp_path / "stack.tif")
    assert cv2.imwritemulti(p, pages(3))
    items = scan(str(tmp_path))
    assert [i.name for i in items] == ["stack.tif [page 1]",
                                       "stack.tif [page 2]",
                                       "stack.tif [page 3]"]
    assert [i.frame for i in items] == [0, 1, 2]
    assert [i.run_number for i in items] == [1, 2, 3]
    assert len({i.key for i in items}) == 3           # results keep apart
    for it, want in zip(items, pages(3)):
        assert np.array_equal(load_item(it), want.astype(np.float32))


def test_a_page_counts_like_the_same_image_on_its_own(tmp_path):
    cv2.imwritemulti(str(tmp_path / "stack.tif"), pages(3))
    single = tmp_path / "one"
    single.mkdir()
    cv2.imwrite(str(single / "p2.tif"), pages(3)[1])
    by_page = analyse(scan(str(tmp_path / "stack.tif"))[1], DetectionParams())
    alone = analyse(scan(str(single))[0], DetectionParams())
    assert by_page.n == alone.n == GOLDEN["frame_1.tiff"]["count"]
    assert [(s.x, s.y, s.luminosity) for s in by_page.spots] == \
        [(s.x, s.y, s.luminosity) for s in alone.spots]


def test_pages_of_a_tiff_in_a_run_folder_keep_the_run_number(tmp_path):
    d = tmp_path / "pbar_run_42"
    d.mkdir()
    cv2.imwritemulti(str(d / "camera.tif"), pages(2))
    items = scan(str(tmp_path))
    assert [(i.run_number, i.name, i.folder) for i in items] == [
        (42, "42 [page 1]", str(d)), (42, "42 [page 2]", str(d))]


# ── A4: bit depth ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("bits", [10, 12, 16])
def test_integer_images_keep_the_bit_depth_rule(tmp_path, bits):
    """A 10/12/16-bit image is scaled by its full scale, as in 1.0: the
    same frame stored at a higher bit depth counts the same spots."""
    full = 2 ** bits - 1
    img = np.round(frame_1().astype(np.float64) * full / 255).astype(np.uint16)
    p = str(tmp_path / "deep.tif")
    cv2.imwrite(p, img)
    got = load_image(p)
    assert np.array_equal(got, img.astype(np.float32))      # values as stored
    scaled = to_float(got)
    assert abs(float(scaled.max()) - frame_1().max()) < 0.5
    spots, _ = detect(scaled, DetectionParams())
    assert len(spots) == GOLDEN["frame_1.tiff"]["count"]


def test_a_float_image_on_the_8_bit_scale_gives_the_golden_numbers(tmp_path):
    p = str(tmp_path / "float.tif")
    assert cv2.imwrite(p, frame_1().astype(np.float32))
    assert load_image(p).dtype == np.float32
    assert_golden(p)


def test_a_float_image_between_0_and_1_is_a_fraction_of_full_scale():
    img = np.array([[0.0, 0.5, 1.0]], np.float32)
    assert np.allclose(to_grey(img), [[0.0, 127.5, 255.0]])


def test_a_float_image_above_1_keeps_its_values():
    img = np.array([[0.0, 1.5, 200.0], [3000.0, -2.0, 7.0]], np.float32)
    assert np.array_equal(to_grey(img), img)


def test_nan_and_infinite_pixels_become_zero():
    img = np.array([[np.nan, np.inf, -np.inf, 100.0]], np.float32)
    assert np.array_equal(to_grey(img), [[0, 0, 0, 100.0]])


def test_integer_images_are_never_rescaled_by_the_float_rule():
    img = np.array([[0, 1]], np.uint8)                  # max <= 1, integer
    assert np.array_equal(to_grey(img), [[0.0, 1.0]])


# ── A5: video ───────────────────────────────────────────────────────────────

LEVELS = [30, 60, 90, 120, 150, 180]


def write_video(path, fourcc):
    """A short grey video: frame k is flat at LEVELS[k], with a bright spot
    that moves 10 px per frame."""
    h, w = 64, 96
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*fourcc), 10,
                          (w, h))
    assert out.isOpened(), f"no {fourcc} writer in this OpenCV"
    for k, level in enumerate(LEVELS):
        img = np.full((h, w), level, np.uint8)
        img[20:30, 10 + 10 * k:20 + 10 * k] = 250
        out.write(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))
    out.release()
    return str(path)


@pytest.fixture
def videos(tmp_path):
    yield {".avi": write_video(tmp_path / "clip.avi", "MJPG"),
           ".mp4": write_video(tmp_path / "clip.mp4", "mp4v")}
    close_videos()                                     # let Windows delete them


@pytest.mark.parametrize("ext", [".avi", ".mp4"])
def test_each_frame_of_a_video_is_one_item(videos, ext):
    items = scan(videos[ext])
    assert [i.name for i in items] == [f"clip{ext} [frame {k}]"
                                       for k in range(6)]
    assert [i.frame for i in items] == [0, 1, 2, 3, 4, 5]
    assert [i.run_number for i in items] == [0, 1, 2, 3, 4, 5]
    for k in (4, 1, 5, 0, 2, 3):                       # any order
        img = load_item(items[k])
        assert img.ndim == 2 and img.dtype == np.float32
        assert abs(float(np.median(img)) - LEVELS[k]) < 4
        col = int(np.argmax(img[25]))
        assert 10 + 10 * k <= col < 20 + 10 * k        # the spot of frame k


def test_a_frame_range_picks_frames_like_python_range(videos):
    p = videos[".avi"]
    assert [i.frame for i in scan(p, frames=(1, 5))] == [1, 2, 3, 4]
    assert [i.frame for i in scan(p, frames=(0, 6, 2))] == [0, 2, 4]
    assert [i.frame for i in scan(p, frames=range(3, 100))] == [3, 4, 5]
    got = scan(p, frames=(10, 20))
    assert got == [] and "has 6 frames" in got.skipped[0].reason
    assert list(frame_range(None, 3)) == [0, 1, 2]


def test_videos_in_a_folder_are_read_with_the_images(videos, tmp_path):
    cv2.imwrite(str(tmp_path / "still.png"), frame_1())
    names = [i.name for i in scan(str(tmp_path))]
    assert names[:6] == [f"clip.avi [frame {k}]" for k in range(6)]
    assert names[6:12] == [f"clip.mp4 [frame {k}]" for k in range(6)]
    assert names[12:] == ["still"]


def test_frames_are_read_only_when_needed(videos, monkeypatch):
    """scan() reads no frame; loading one frame reads one frame."""
    reads = []
    original = cv2.VideoCapture

    class Counting:
        def __init__(self, path):
            self.cap = original(path)

        def read(self):
            reads.append(1)
            return self.cap.read()

        def __getattr__(self, name):
            return getattr(self.cap, name)

    close_videos()
    monkeypatch.setattr(loading.cv2, "VideoCapture", Counting)
    items = scan(videos[".avi"])
    assert len(items) == 6 and reads == []
    load_item(items[3])
    assert len(reads) == 1
    load_item(items[4])                                # the next one: no seek
    assert len(reads) == 2
    close_videos()


def test_a_broken_video_is_reported(tmp_path):
    p = tmp_path / "broken.avi"
    p.write_bytes(b"not a video at all")
    got = scan(str(p))
    assert got == [] and "could not be opened" in got.skipped[0].reason


def test_a_video_frame_is_analysed_like_an_image(videos):
    r = analyse(scan(videos[".avi"])[2], DetectionParams())
    assert r.ok and r.info is not None
    bad = analyse(Item(videos[".avi"], 0, "", frame=99), DetectionParams())
    assert bad.error == "could not read image"
