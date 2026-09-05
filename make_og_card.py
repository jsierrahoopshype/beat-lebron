#!/usr/bin/env python3
"""
Builds og-beat-lebron.png (1200x630), the social preview card for Beat LeBron.

Default: LeBron's headshot from the nba-headshots repo inside a gold medallion on the right,
title and hook text on the left. Optional: --photo some.jpg uses a licensed photo full-bleed
on the right half instead (faded into the dark background), the 73-9 style.

    python make_og_card.py                       # headshot version
    python make_og_card.py --photo lebron.jpg    # licensed-photo version
    python make_og_card.py --title "BEAT LEBRON" --hook "Two All-Stars vs. the King"

Needs Pillow (pip install pillow). Fonts are fetched once from the google/fonts repo if
they are not next to the script.
"""
import argparse, io, os, sys, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1200, 630
GOLD, WHITE, GREY, BG = (242, 183, 5), (255, 255, 255), (201, 201, 214), (10, 10, 15)
FONTS = {
    "BarlowCondensed-ExtraBold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/barlowcondensed/BarlowCondensed-ExtraBold.ttf",
    "BarlowCondensed-Bold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/barlowcondensed/BarlowCondensed-Bold.ttf",
}
HEADSHOT = "https://raw.githubusercontent.com/jsierrahoopshype/nba-headshots/main/players/headshots/face2/2544-lebron-james.png"
# The medallion is cut from the licensed hero photo when it is there: the CDN headshot is a square
# with empty space above the head and a hard edge below it, which left black bands inside the disc.
def _face_src():
    for c in (os.path.join(HERE, "lebron-hero.jpg"),
              os.path.join(HERE, "..", "beat-lebron", "lebron-hero.jpg"),
              os.path.join(HERE, "..", "lebron-hero.jpg")):
        if os.path.exists(c):
            return c
    return ""
FACE_SRC = _face_src()


def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def font(name, size):
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        open(path, "wb").write(fetch(FONTS[name]))
    return ImageFont.truetype(path, size)


def radial(size, color, alpha_center, feather=1.0):
    """Soft radial glow as an RGBA layer."""
    s = size
    layer = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(layer)
    steps = 40
    for i in range(steps, 0, -1):
        r = int(s / 2 * i / steps)
        a = int(alpha_center * (1 - i / steps) ** feather)
        d.ellipse((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), fill=a)
    out = Image.new("RGBA", (s, s), color + (0,))
    out.putalpha(layer)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photo", help="licensed photo to use full-bleed on the right (jpg/png)")
    ap.add_argument("--title", default="BEAT LEBRON")
    ap.add_argument("--hook", default="Pick the two All-Stars who out-stat LeBron James. Only one duo works.")
    ap.add_argument("--face", help="photo to cut the medallion from (default: the hero photo in the game repo)")
    ap.add_argument("--facezoom", type=float, default=0.78, help="square crop side as a share of the photo width")
    ap.add_argument("--facex", type=float, default=0.50, help="crop centre x, 0-1")
    ap.add_argument("--facey", type=float, default=0.20, help="crop centre y, 0-1")
    ap.add_argument("--out", default=os.path.join(HERE, "og-beat-lebron.png"))
    a = ap.parse_args()

    im = Image.new("RGBA", (W, H), BG + (255,))
    # washes: gold top-right, purple bottom-left
    im.alpha_composite(radial(1400, GOLD, 95), (W - 700, -700))
    im.alpha_composite(radial(1300, (85, 37, 131), 150), (-650, H - 650))

    if a.photo:
        ph = Image.open(a.photo).convert("RGBA")
        # cover the right 58% of the card, fade the left edge into the background
        target_h = H
        ph = ph.resize((int(ph.width * target_h / ph.height), target_h))
        x0 = W - ph.width
        mask = Image.new("L", ph.size, 255)
        md = ImageDraw.Draw(mask)
        fade = 260
        for i in range(fade):
            md.line([(i, 0), (i, H)], fill=int(255 * i / fade))
        ph.putalpha(mask)
        im.alpha_composite(ph, (max(x0, W - int(W * .58)), 0))
        text_w = W - int(W * .55)
    else:
        D = 470
        src_path = a.face or FACE_SRC
        if src_path and os.path.exists(src_path):
            # square crop around the head, so the photo fills the whole disc edge to edge
            src = Image.open(src_path).convert("RGB")
            side = int(src.width * a.facezoom)
            cx = int(src.width * a.facex)
            cy = int(src.height * a.facey)
            x0 = max(0, min(src.width - side, cx - side // 2))
            y0 = max(0, min(src.height - side, cy - side // 2))
            face = src.crop((x0, y0, x0 + side, y0 + side)).convert("RGBA")
        else:
            face = Image.open(io.BytesIO(fetch(HEADSHOT))).convert("RGBA")
        face = face.resize((D, D), Image.LANCZOS)
        cx, cy = W - 300, H // 2
        # glow + ring + clipped face
        im.alpha_composite(radial(D + 260, GOLD, 120, 1.6), (cx - (D + 260) // 2, cy - (D + 260) // 2))
        ring = Image.new("RGBA", (D + 28, D + 28), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((0, 0, D + 27, D + 27), fill=GOLD + (255,))
        im.alpha_composite(ring, (cx - (D + 28) // 2, cy - (D + 28) // 2))
        # a photo crop already fills the disc; the CDN headshot still needs the 1.15 zoom so its
        # hard bottom edge falls outside the circle
        Z = int(D * (1.0 if (src_path and os.path.exists(src_path)) else 1.15))
        big = face.resize((Z, Z), Image.LANCZOS)
        disc = Image.new("RGBA", (D, D), (0, 0, 0, 0))
        disc.alpha_composite(big, ((D - Z) // 2, (D - Z) // 2))
        m = Image.new("L", (D, D), 0)
        ImageDraw.Draw(m).ellipse((0, 0, D - 1, D - 1), fill=255)
        disc.putalpha(m)
        im.alpha_composite(disc, (cx - D // 2, cy - D // 2))
        text_w = cx - D // 2 - 90

    d = ImageDraw.Draw(im)
    x = 64
    # title, shrunk to fit the text column
    size = 168
    while size > 90:
        f = font("BarlowCondensed-ExtraBold.ttf", size)
        if d.textlength(a.title, font=f) <= text_w:
            break
        size -= 6
    d.text((x, 118), a.title, font=f, fill=GOLD)
    # hook, wrapped
    hf = font("BarlowCondensed-Bold.ttf", 54)
    words, lines, cur = a.hook.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=hf) <= text_w:
            cur = t
        else:
            lines.append(cur); cur = wd
    lines.append(cur)
    y = 118 + size + 20
    for ln in lines[:3]:
        d.text((x, y), ln, font=hf, fill=WHITE)
        y += 62
    sf = font("BarlowCondensed-Bold.ttf", 34)
    d.text((x, y + 22), "6 ALL-STARS  ·  5 LIVES  ·  15 SECONDS", font=sf, fill=GREY)
    d.text((x, H - 92), "HOOPSMATIC.COM/BEAT-LEBRON", font=font("BarlowCondensed-Bold.ttf", 36), fill=GOLD)
    d.rounded_rectangle((16, 16, W - 17, H - 17), radius=22, outline=(255, 255, 255, 26), width=3)

    im.convert("RGB").save(a.out, "PNG", optimize=True)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
