"""
Renderiza o card "CURIOSIDADE HISTÓRICA" (1080x1080) para o @historiasreais00.
Template determinístico com Pillow: sem IA, sem custo, sempre igual.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W = H = 1080
HANDLE = "@historiasreais00"

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONT_REG_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _font(paths, size):
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    try:
        import matplotlib, os as _os
        d = _os.path.join(_os.path.dirname(matplotlib.__file__), "mpl-data/fonts/ttf")
        return ImageFont.truetype(_os.path.join(d, "DejaVuSans-Bold.ttf"), size)
    except Exception:
        return ImageFont.load_default()


def lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def vertical_gradient(size, stops):
    """stops: [(pos 0..1, (r,g,b)), ...] - degradê vertical suave."""
    w, h = size
    img = Image.new("RGB", (1, h))
    px = img.load()
    stops = sorted(stops)
    for y in range(h):
        t = y / max(1, h - 1)
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                local = 0 if p1 == p0 else (t - p0) / (p1 - p0)
                px[0, y] = lerp(c0, c1, local)
                break
        else:
            px[0, y] = stops[-1][1]
    return img.resize((w, h), Image.BILINEAR)


def draw_sun(img, cx, cy, radius):
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, a in ((radius * 3.2, 40), (radius * 2.2, 80), (radius * 1.5, 130)):
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 170, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(radius * 0.7))
    img.paste(Image.blend(img, Image.composite(glow, img, glow.convert("L")), 0.55), (0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(255, 214, 150))


def draw_pyramids(img, base_y):
    d = ImageDraw.Draw(img, "RGBA")
    dark = (9, 9, 18, 255)
    # pirâmide grande
    d.polygon([(200, base_y), (520, base_y - 250), (840, base_y)], fill=dark)
    # pirâmide média (direita, atrás)
    d.polygon([(700, base_y), (880, base_y - 170), (1060, base_y)], fill=dark)
    # pirâmide pequena (frente, esquerda)
    d.polygon([(90, base_y), (300, base_y - 125), (500, base_y)], fill=dark)
    # chão
    d.rectangle([0, base_y, W, H], fill=(7, 7, 14, 255))


def wrap(draw, text, font, max_width):
    words, lines, cur = text.split(), [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if draw.textlength(test, font=font) <= max_width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_centered_block(draw, lines, font, y, fill, line_gap=14):
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((W - w) / 2, y), line, font=font, fill=fill)
        y += font.size + line_gap
    return y


def render(headline, subtext, out_path):
    img = vertical_gradient((W, H), [
        (0.00, (12, 16, 34)),
        (0.30, (40, 33, 58)),
        (0.55, (128, 74, 62)),
        (0.68, (214, 124, 62)),
        (0.78, (250, 178, 96)),
        (1.00, (246, 200, 130)),
    ])

    horizon = int(H * 0.86)
    draw_sun(img, W // 2, horizon - 130, 72)
    draw_pyramids(img, horizon)

    d = ImageDraw.Draw(img, "RGBA")

    # selo pill "CURIOSIDADE HISTÓRICA"
    pill_font = _font(FONT_CANDIDATES, 30)
    label = "CURIOSIDADE HISTÓRICA"
    tw = d.textlength(label, font=pill_font)
    pad_x, pad_y = 34, 18
    pw, ph = tw + pad_x * 2, pill_font.size + pad_y * 2
    px, py = (W - pw) / 2, 86
    d.rounded_rectangle([px, py, px + pw, py + ph], radius=ph / 2,
                        fill=(10, 12, 24, 150), outline=(255, 255, 255, 110), width=2)
    d.text((px + pad_x, py + pad_y - 3), label, font=pill_font, fill=(255, 255, 255, 235))

    # manchete (no máximo 3 linhas, sempre acima das pirâmides)
    h_font = _font(FONT_CANDIDATES, 88)
    h_lines = wrap(d, headline, h_font, 900)
    while len(h_lines) > 3 and h_font.size > 52:
        h_font = _font(FONT_CANDIDATES, h_font.size - 4)
        h_lines = wrap(d, headline, h_font, 900)
    y = draw_centered_block(d, h_lines, h_font, 292, (255, 255, 255), line_gap=8)

    # texto de apoio (fica entre a manchete e o topo das pirâmides)
    s_font = _font(FONT_REG_CANDIDATES, 33)
    s_lines = wrap(d, subtext, s_font, 800)
    s_y = min(y + 26, 610)
    draw_centered_block(d, s_lines, s_font, s_y, (253, 238, 215), line_gap=10)

    # rodapé
    f_font = _font(FONT_CANDIDATES, 34)
    footer = f"Siga {HANDLE} →"
    fw = d.textlength(footer, font=f_font)
    d.text(((W - fw) / 2, H - 92), footer, font=f_font, fill=(255, 255, 255, 240))

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    # JPEG porque a API do Instagram só aceita JPEG no feed
    img.convert("RGB").save(out_path, "JPEG", quality=95, subsampling=0, optimize=True)
    return out_path


if __name__ == "__main__":
    render(
        "Cleópatra viveu mais perto da Lua do que das pirâmides",
        "A Grande Pirâmide já tinha 2.500 anos quando ela nasceu",
        "images/teste.jpg",
    )
    print("ok")
