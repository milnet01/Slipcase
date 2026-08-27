"""PNG export utilities with optimised compression."""

import numpy as np
from PIL import Image


def save_optimized_png(image: Image.Image, path: str, compress_level: int = 6) -> None:
    """Save a PNG with compression and imperceptible quality reduction.

    Applies three optimizations:
    - Strips lowest bit of each colour channel (invisible, ~15% smaller)
    - Quantizes semi-transparent alpha to multiples of 4 (~0-1% smaller)
    - Drops alpha channel entirely when image is fully opaque (~15% smaller)

    Args:
        compress_level: zlib compression 0-9. Default 6 balances speed and
            size (~5% larger than 9 but 2-4x faster). Use 9 for maximum
            compression when file size matters more than export speed.
    """
    arr = np.array(image)
    if image.mode == "RGBA":
        arr[:, :, :3] = arr[:, :, :3] & 0xFE
        a = arr[:, :, 3]
        mask = (a > 0) & (a < 255)
        a[mask] = ((a[mask].astype(np.uint16) + 2) // 4 * 4).clip(1, 254).astype(np.uint8)
        if a.min() == 255:
            save_img = Image.fromarray(arr[:, :, :3], "RGB")
        else:
            save_img = Image.fromarray(arr, "RGBA")
    elif image.mode == "RGB":
        arr &= 0xFE
        save_img = Image.fromarray(arr, "RGB")
    else:
        save_img = image
    save_img.save(path, "PNG", compress_level=compress_level)
