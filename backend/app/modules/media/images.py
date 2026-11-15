"""Image validation and normalisation.

Every upload is decoded and re-encoded as WebP. That (a) proves it is really an
image, (b) strips EXIF metadata such as GPS location, (c) removes any payload
hidden inside the original file, and (d) shrinks it. We never store the
uploaded bytes as-is and never trust the client's filename or content type.
"""

import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import UnsupportedMediaError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_DIMENSION = 2048
AVATAR_SIZE = 400

# Images above 2x this many pixels raise DecompressionBombError (zip-bomb style attack).
Image.MAX_IMAGE_PIXELS = 20_000_000


@dataclass(frozen=True)
class ProcessedImage:
    data: bytes
    width: int
    height: int
    content_type: str = "image/webp"


def process_image(raw: bytes, *, square: int | None = None) -> ProcessedImage:
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            image_format = probe.format
            probe.verify()
        if image_format not in ALLOWED_FORMATS:
            raise UnsupportedMediaError("Only JPEG, PNG and WebP images are allowed")

        # verify() leaves the file unusable, so open it again for real work.
        with Image.open(io.BytesIO(raw)) as source:
            image = ImageOps.exif_transpose(source)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if image.mode in ("P", "LA", "PA") else "RGB")
            if square is not None:
                image = ImageOps.fit(image, (square, square), Image.Resampling.LANCZOS)
            else:
                image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="WEBP", quality=85, method=4)
            return ProcessedImage(
                data=output.getvalue(), width=image.width, height=image.height
            )
    except UnsupportedMediaError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise UnsupportedMediaError() from None
