"""Génère l'icône de l'application (PNG + ICO Windows) sans dépendance externe."""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent


def draw_icon(size: int) -> Image.Image:
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # fond arrondi
    r = int(s * 0.22)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=r, fill=(13, 16, 23, 255))
    # dégradé simulé (bandes diagonales)
    grad = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for i in range(s):
        t = i / s
        col = (int(59 + (0 - 59) * t), int(123 + (194 - 123) * t), int(255 + (168 - 255) * t), 255)
        gd.line([(i, 0), (i, s)], fill=col)
    mask = Image.new("L", (s, s), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, s - 1, s - 1], radius=r, fill=255)
    img.paste(grad, (0, 0), mask)
    # lettre D
    w = int(s * 0.10)
    d.line([(int(s * 0.32), int(s * 0.26)), (int(s * 0.32), int(s * 0.74))], fill="white", width=w)
    d.arc([int(s * 0.28), int(s * 0.26), int(s * 0.74), int(s * 0.74)], start=-90, end=90, fill="white", width=w)
    # point accent
    d.ellipse([int(s * 0.70), int(s * 0.70), int(s * 0.84), int(s * 0.84)], fill=(0, 194, 168, 255))
    return img


if __name__ == "__main__":
    icon = draw_icon(512)
    icon.save(OUT / "delivra.png")
    icon.save(OUT / "delivra.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("Icônes générées :", OUT / "delivra.ico")
