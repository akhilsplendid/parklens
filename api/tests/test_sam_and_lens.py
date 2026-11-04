import asyncio
import io

import pytest

from parklens import sam
from parklens.config import Settings
from parklens.schemas import Child, Party
from parklens.services.lens import LensService
from tests.conftest import FakeClient

RAW = (
    "<0f>0<|box;x1=353;y1=382;x2=453;y2=427;w=537;h=561|><|mask;x=0;y=0;data=46,101,!|>"
    ",1<|box;x1=10;y1=20;x2=300;y2=400;w=537;h=561;c=0.91|><|mask;x=0;y=0;data=1,2|>"
)


def test_parse_boxes():
    boxes = sam.parse_boxes(RAW)
    assert [b.object_id for b in boxes] == [0, 1]
    assert boxes[1].confidence == 0.91 and boxes[0].confidence is None
    big = sam.largest(boxes)
    assert big.object_id == 1 and 0.3 < big.area_fraction < 0.5
    assert sam.parse_boxes("") == []


def test_box_scaling():
    b = sam.parse_boxes(RAW)[1].scaled(1074, 1122)
    assert (b.x1, b.y1, b.x2, b.y2) == (20, 40, 600, 800)


def _jpeg(w=640, h=480):
    PIL = pytest.importorskip("PIL.Image")
    im = PIL.new("RGB", (w, h), (120, 90, 40))
    buf = io.BytesIO()
    im.save(buf, "JPEG")
    return buf.getvalue()


def test_crop_and_downscale():
    PIL = pytest.importorskip("PIL.Image")
    data = _jpeg(2000, 1500)
    small, mime = sam.downscale(data, 1280)
    assert mime == "image/jpeg" and max(PIL.open(io.BytesIO(small)).size) == 1280
    crop = sam.crop(small, sam.parse_boxes(RAW)[1])
    assert PIL.open(io.BytesIO(crop)).size[0] > 100


def test_lens_identifies_and_narrates_from_park_text(kb):
    pytest.importorskip("PIL.Image")
    fake = FakeClient(
        answers={
            "SpeciesId": {
                "species_id": "tiger",
                "confidence": 0.93,
                "what_i_see": "a big striped cat",
            },
            "Narration": {
                "narration": "That's an Amur tiger, the biggest cat in the world!",
                "fun_fact": "It lives along the Amur river.",
            },
        },
        sam_raw=RAW,
    )
    svc = LensService(kb, fake, Settings(model_api_key="x"))
    party = Party(children=[Child(name="Mia", age=5, height_cm=110)], language="sv")
    r = asyncio.run(svc.analyze(_jpeg(), party))
    assert r.found and r.species_id == "tiger" and r.scientific_name == "Panthera tigris altaica"
    assert r.source_url == "https://example.test/djur/tiger" and r.language == "sv"
    assert r.box["n_found"] == 2
    # The narration prompt carries the park text and the audience, and nothing else as facts.
    narr_msgs = next(m for n, m in fake.calls if n == "Narration")
    assert "Amurfloden" in narr_msgs[0]["content"] and "5-year-old" in narr_msgs[0]["content"]
    # Second identical frame is served from cache without new model calls.
    n_calls = len(fake.calls)
    r2 = asyncio.run(svc.analyze(_jpeg(), party))
    assert r2.cached and len(fake.calls) == n_calls


def test_lens_no_animal(kb):
    pytest.importorskip("PIL.Image")
    fake = FakeClient(
        {"SpeciesId": {"species_id": "none", "confidence": 0.1, "what_i_see": "grass"}}, sam_raw=""
    )
    svc = LensService(kb, fake, Settings(model_api_key="x"))
    r = asyncio.run(svc.analyze(_jpeg()))
    assert not r.found and "can't spot" in r.narration


def test_lens_unlisted_species(kb):
    pytest.importorskip("PIL.Image")
    fake = FakeClient(
        {"SpeciesId": {"species_id": "none", "confidence": 0.4, "what_i_see": "a dog"}}, sam_raw=RAW
    )
    r = asyncio.run(LensService(kb, fake, Settings(model_api_key="x")).analyze(_jpeg()))
    assert r.found and r.species_id is None and "a dog" in r.narration


def test_warm_prefills_narration_cache(kb):
    pytest.importorskip("PIL.Image")
    fake = FakeClient(
        {"Narration": {"narration": "Hello tiger.", "fun_fact": "Stripes."}}, sam_raw=RAW
    )
    svc = LensService(kb, fake, Settings(model_api_key="x"))
    n = asyncio.run(svc.warm(None, ["tiger", "lodjur", "wildfire", "nope"]))
    assert n == 2 and sum(1 for c in fake.calls if c[0] == "Narration") == 2
    # A later look at the tiger needs SAM + ID only, no new narration call.
    fake.answers["SpeciesId"] = {"species_id": "tiger", "confidence": 0.9, "what_i_see": "cat"}
    before = sum(1 for c in fake.calls if c[0] == "Narration")
    r = asyncio.run(svc.analyze(_jpeg()))
    assert r.narration == "Hello tiger."
    assert sum(1 for c in fake.calls if c[0] == "Narration") == before


def test_open_handles_exif_rotation_and_garbage():
    import io

    import pytest
    from PIL import Image

    from parklens import sam

    im = Image.new("RGB", (400, 200), "red")
    buf = io.BytesIO()
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: rotate 90° on display, as phones do for portrait shots
    im.save(buf, "JPEG", exif=exif)
    out, _ = sam.downscale(buf.getvalue(), 1280)
    assert Image.open(io.BytesIO(out)).size == (200, 400)
    with pytest.raises(sam.BadImage):
        sam.downscale(b"not an image", 1280)


def test_lens_caches_misses_and_warm_dedupes(kb):
    import asyncio

    from parklens.config import Settings
    from parklens.services.lens import LensService
    from tests.conftest import FakeClient

    fake = FakeClient(
        {"SpeciesId": {"species_id": "none", "confidence": 0.1, "what_i_see": "grass"}}, sam_raw=""
    )
    svc = LensService(kb, fake, Settings(model_api_key="x"))
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "green").save(buf, "JPEG")
    r1 = asyncio.run(svc.analyze(buf.getvalue()))
    r2 = asyncio.run(svc.analyze(buf.getvalue()))
    assert not r1.found and r2.cached
    before = len(fake.calls)
    fake.answers["Narration"] = {"narration": "x", "fun_fact": "y"}
    n = asyncio.run(svc.warm(None, ["tiger"] * 50 + ["nope"]))
    assert n == 1 and len(fake.calls) == before + 1
