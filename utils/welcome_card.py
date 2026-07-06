import io
import math
from PIL import Image, ImageDraw, ImageFont

def _circle_avatar(avatar_bytes: bytes, size: int) -> Image.Image:
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((size, size))
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    result = Image.new("RGBA", (size, size))
    result.paste(avatar, (0, 0), mask)
    return result

def _get_font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except Exception:
        return ImageFont.load_default(size=size) if hasattr(ImageFont, "load_default") else ImageFont.load_default()

def generate_welcome_card(avatar_bytes: bytes, username: str, member_count: int) -> io.BytesIO:
    width, height = 900, 300
    img = Image.new("RGB", (width, height), (10, 30, 60))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        ratio = y / height
        r = int(10 + ratio * 20)
        g = int(50 + ratio * 60)
        b = int(90 + ratio * 100)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    draw.ellipse((width - 160, -60, width - 20, 80), fill=(255, 200, 80))

    for wave_y in [220, 245, 270]:
        points = []
        for x in range(0, width + 20, 20):
            offset = 10 * math.sin((x / 40) + wave_y)
            points.append((x, wave_y + offset))
        draw.line(points, fill=(255, 255, 255), width=2, joint="curve")

    avatar_size = 150
    avatar = _circle_avatar(avatar_bytes, avatar_size)
    avatar_pos = (40, (height - avatar_size) // 2)
    border = Image.new("RGBA", (avatar_size + 10, avatar_size + 10), (0, 0, 0, 0))
    ImageDraw.Draw(border).ellipse((0, 0, avatar_size + 10, avatar_size + 10), fill=(255, 255, 255, 255))
    img.paste(border, (avatar_pos[0] - 5, avatar_pos[1] - 5), border)
    img.paste(avatar, avatar_pos, avatar)

    title_font = _get_font(42)
    sub_font = _get_font(24)
    small_font = _get_font(20)

    text_x = 220
    draw.text((text_x, 70), "BIENVENUE À BORD", font=title_font, fill=(255, 255, 255))
    draw.text((text_x, 130), username, font=sub_font, fill=(255, 215, 0))
    draw.text((text_x, 170), f"Membre n°{member_count}", font=small_font, fill=(200, 220, 255))

    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
