#!/usr/bin/env python3

import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "icons"
SIZES = (16, 32, 48, 128)

BACKGROUND = (91, 59, 34, 255)
HIGHLIGHT = (196, 161, 113, 255)
CAPSULE = (247, 239, 224, 255)
SHADOW = (56, 36, 21, 255)


def chunk(kind: bytes, data: bytes) -> bytes:
    payload = kind + data
    return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)


def blend(base: tuple[int, int, int, int], overlay: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    alpha = overlay[3] / 255
    inverse = 1 - alpha
    return (
        round(overlay[0] * alpha + base[0] * inverse),
        round(overlay[1] * alpha + base[1] * inverse),
        round(overlay[2] * alpha + base[2] * inverse),
        255,
    )


def rounded_square_pixel(x: int, y: int, size: int) -> bool:
    margin = max(1, size // 16)
    radius = max(3, size // 5)
    left = margin
    right = size - margin - 1
    top = margin
    bottom = size - margin - 1

    if left + radius <= x <= right - radius or top + radius <= y <= bottom - radius:
        return left <= x <= right and top <= y <= bottom

    corner_x = left + radius if x < left + radius else right - radius
    corner_y = top + radius if y < top + radius else bottom - radius
    return (x - corner_x) ** 2 + (y - corner_y) ** 2 <= radius**2


def capsule_pixel(x: int, y: int, size: int, offset: int = 0) -> bool:
    cx = size * 0.5 + offset
    cy = size * 0.52 + offset
    width = size * 0.62
    height = size * 0.28
    angle = -0.48

    dx = x - cx
    dy = y - cy
    rx = dx * 0.887 + dy * -0.462
    ry = dx * 0.462 + dy * 0.887

    body_width = width - height
    radius = height / 2
    if abs(rx) <= body_width / 2 and abs(ry) <= radius:
        return True

    left_center = -body_width / 2
    right_center = body_width / 2
    return (
        (rx - left_center) ** 2 + ry**2 <= radius**2
        or (rx - right_center) ** 2 + ry**2 <= radius**2
    )


def highlight_pixel(x: int, y: int, size: int) -> bool:
    cx = size * 0.36
    cy = size * 0.30
    rx = size * 0.20
    ry = size * 0.08
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1


def pixel(x: int, y: int, size: int) -> tuple[int, int, int, int]:
    if not rounded_square_pixel(x, y, size):
        return (0, 0, 0, 0)

    color = BACKGROUND
    if highlight_pixel(x, y, size):
        color = blend(color, HIGHLIGHT)
    if capsule_pixel(x, y, size, offset=max(1, size // 28)):
        color = SHADOW
    if capsule_pixel(x, y, size):
        color = CAPSULE

    return color


def png_bytes(size: int) -> bytes:
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            row.extend(pixel(x, y, size))
        rows.append(bytes(row))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            chunk(b"IHDR", ihdr),
            chunk(b"IDAT", zlib.compress(b"".join(rows), level=9)),
            chunk(b"IEND", b""),
        ]
    )


def main() -> None:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        (ICON_DIR / f"icon-{size}.png").write_bytes(png_bytes(size))


if __name__ == "__main__":
    main()
