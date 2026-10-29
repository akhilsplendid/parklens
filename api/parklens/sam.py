"""Parse SAM 3.1 output and crop the matched object.

SAM 3.1 answers in a special-token grammar, one line per frame, e.g.
    <0f>0<|box;x1=353;y1=382;x2=453;y2=427;w=537;h=561|><|mask;x=0;y=0;data=...|>,1<|box;...|>...
Boxes are all the Lens needs (we crop and hand the crop to Muse Spark), so we parse them with a
regex and keep no dependency. `meta_sam_parser` is used only when a caller wants masks.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

_BOX_RE = re.compile(
    r"(?:(?:^|<\d+f>|,)(?P<id>\d+))?<\|box;x1=(?P<x1>\d+);y1=(?P<y1>\d+);x2=(?P<x2>\d+);"
    r"y2=(?P<y2>\d+);w=(?P<w>\d+);h=(?P<h>\d+)(?:;c=(?P<c>[0-9.]+))?\|>"
)


@dataclass(frozen=True)
class Box:
    object_id: int
    x1: int
    y1: int
    x2: int  # inclusive, as on the wire
    y2: int
    width: int  # media size the coordinates refer to
    height: int
    confidence: float | None = None

    @property
    def area(self) -> int:
        return max(0, self.x2 - self.x1 + 1) * max(0, self.y2 - self.y1 + 1)

    @property
    def area_fraction(self) -> float:
        return self.area / float(self.width * self.height or 1)

    def scaled(self, target_w: int, target_h: int) -> Box:
        """Map wire coordinates onto an image of a different size."""
        fx, fy = target_w / self.width, target_h / self.height
        return Box(
            self.object_id,
            round(self.x1 * fx),
            round(self.y1 * fy),
            round(self.x2 * fx),
            round(self.y2 * fy),
            target_w,
            target_h,
            self.confidence,
        )


def parse_boxes(raw: str) -> list[Box]:
    boxes = []
    for i, m in enumerate(_BOX_RE.finditer(raw)):
        boxes.append(
            Box(
                object_id=int(m["id"]) if m["id"] is not None else i,
                x1=int(m["x1"]),
                y1=int(m["y1"]),
                x2=int(m["x2"]),
                y2=int(m["y2"]),
                width=int(m["w"]),
                height=int(m["h"]),
                confidence=float(m["c"]) if m["c"] else None,
            )
        )
    return boxes


def largest(boxes: list[Box]) -> Box | None:
    return max(boxes, key=lambda b: b.area, default=None)


def crop(image: bytes, box: Box, pad: float = 0.12, max_side: int = 768) -> bytes:
    """Crop the box (with padding) out of a JPEG/PNG and return a JPEG."""
    from PIL import Image

    im = Image.open(io.BytesIO(image)).convert("RGB")
    b = box.scaled(*im.size)
    pw, ph = int((b.x2 - b.x1) * pad), int((b.y2 - b.y1) * pad)
    region = (
        max(0, b.x1 - pw),
        max(0, b.y1 - ph),
        min(im.width, b.x2 + pw),
        min(im.height, b.y2 + ph),
    )
    out = im.crop(region)
    out.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def downscale(image: bytes, max_side: int) -> tuple[bytes, str]:
    """Shrink a camera frame before upload. Returns (jpeg_bytes, mime)."""
    from PIL import Image

    im = Image.open(io.BytesIO(image)).convert("RGB")
    if max(im.size) > max_side:
        im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return buf.getvalue(), "image/jpeg"
