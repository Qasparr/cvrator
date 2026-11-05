#!/usr/bin/env python3
# ============================================================================
# 93
# CVRATOR · make_logo.py — the seal, drawn deterministically with PIL.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# Method of Science, Aim of Religion.
#
# MECHANISM: no external assets. A purple field, a gold rim carrying the
# legends CVRATOR / EXEMPLARIA DVPLICIA, a green ring for the third
# colour of the release livery, and at the centre the steward's mark:
# two pages overlapped — the keeper and its echo — bound by a green
# seal-dot struck with a gold check: one copy kept, proven, sealed.
# ============================================================================

import math
import os

from PIL import Image, ImageDraw, ImageFont

PURPLE = (75, 0, 130, 255)        # #4B0082
PURPLE_LT = (104, 32, 160, 255)
GOLD = (255, 215, 0, 255)         # #FFD700
GREEN = (31, 163, 74, 255)        # emerald of the release pair
DARK = (24, 0, 44, 255)

S = 1200
CX = CY = S // 2
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "logo",
                   "cvrator-seal.png")
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def font(sz):
    return ImageFont.truetype(SERIF, sz)


def arc_text(img, text, radius, start_deg, end_deg, fnt, fill,
             flip=False):
    """MECHANISM: set a string along a circular arc, letter by letter,
    each glyph rotated tangent to the ring."""
    if flip:
        # Bottom legend: letters must read left-to-right along the lower
        # arc with their tops toward the centre — so walk the arc in the
        # opposite direction, take the string in reverse, and stand each
        # glyph on the radius (rotation = -angle + 90).
        text = text[::-1]
        start_deg, end_deg = end_deg, start_deg
    n = len(text)
    for i, ch in enumerate(text):
        t = i / max(n - 1, 1)
        ang = math.radians(start_deg + (end_deg - start_deg) * t)
        x = CX + radius * math.cos(ang)
        y = CY + radius * math.sin(ang)
        glyph = Image.new("RGBA", (90, 90), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glyph)
        gd.text((45, 45), ch, font=fnt, fill=fill, anchor="mm")
        rot = -math.degrees(ang) + 90 if flip else -math.degrees(ang) - 90
        glyph = glyph.rotate(rot, expand=True, resample=Image.BICUBIC)
        img.alpha_composite(glyph, (int(x - glyph.width / 2),
                                    int(y - glyph.height / 2)))


def page(draw, x, y, w, h, outline, fill=None, fold=26):
    """MECHANISM: one document glyph — rectangle with a folded corner."""
    if fill:
        draw.rectangle([x, y, x + w, y + h], fill=fill)
    draw.rectangle([x, y, x + w, y + h], outline=outline, width=7)
    draw.polygon([(x + w - fold, y), (x + w, y + fold),
                  (x + w - fold, y + fold)], outline=outline, width=6)


def main():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Field and rims: gold outer, green hairline, purple field.
    d.ellipse([10, 10, S - 10, S - 10], fill=GOLD)
    d.ellipse([34, 34, S - 34, S - 34], fill=DARK)
    d.ellipse([46, 46, S - 46, S - 46], outline=GREEN, width=5)
    d.ellipse([58, 58, S - 58, S - 58], fill=PURPLE)
    # Legends.
    arc_text(img, "CVRATOR", 470, -162, -18, font(96), GOLD)
    arc_text(img, "EXEMPLARIA · DVPLICIA", 462, 168, 12, font(54),
             GOLD, flip=True)
    d = ImageDraw.Draw(img)
    for sx in (-470, 470):
        d.ellipse([CX + sx - 13, CY - 13, CX + sx + 13, CY + 13],
                  fill=GOLD)
    # The steward's mark: keeper page behind-left, echo before-right.
    page(d, CX - 205, CY - 190, 300, 380, GOLD, fill=PURPLE_LT)
    page(d, CX - 95, CY - 110, 300, 380, GOLD, fill=PURPLE)
    # Ruled lines on the front page — the record itself.
    for i in range(4):
        yy = CY + 10 + i * 58
        d.line([CX - 40, yy, CX + 150, yy], fill=GOLD, width=9)
    # The seal-dot: green, struck with the gold check of verification.
    r = 74
    dx, dy = CX + 205, CY + 262
    d.ellipse([dx - r, dy - r, dx + r, dy + r], fill=GREEN,
              outline=GOLD, width=7)
    d.line([dx - 38, dy + 2, dx - 10, dy + 30], fill=GOLD, width=15)
    d.line([dx - 10, dy + 30, dx + 42, dy - 30], fill=GOLD, width=15)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    print("wrote", os.path.normpath(OUT), img.size)


if __name__ == "__main__":
    main()

# 93 — Live, Love, and let Love, Live.
