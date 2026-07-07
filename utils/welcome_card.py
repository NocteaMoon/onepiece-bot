import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def _circle_avatar(avatar_bytes: bytes, size: int) -> Image.Image:
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((size, size))
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    result = Image.new("RGBA", (size, size))
    result.paste(avatar, (0, 0), mask)
    return result

def _get_font(size: int, bold: bool = False):
    try:
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        return ImageFont.truetype(name, size)
    except Exception:
        return ImageFont.load_default(size=size) if hasattr(ImageFont, "load_default") else ImageFont.load_default()

def _cover_resize(img: Image.Image, width: int, height: int) -> Image.Image:
    img_ratio = img.width / img.height
    target_ratio = width / height
    if img_ratio > target_ratio:
        new_height = height
        new_width = int(height * img_ratio)
    else:
        new_width = width
        new_height = int(width / img_ratio)
    img = img.resize((new_width, new_height))
    left = (new_width - width) // 2
    top = (new_height - height) // 2
    return img.crop((left, top, left + width, top + height))

def generate_welcome_card(avatar_bytes: bytes, username: str, member_count: int, background_bytes: bytes = None) -> io.BytesIO:
    width, height = 900, 300

    if background_bytes:
        try:
            bg = Image.open(io.BytesIO(background_bytes)).convert("RGB")
            img = _cover_resize(bg, width, height)
            overlay = Image.new("RGBA", (width, height), (10, 10, 14, 165))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        except Exception:
            background_bytes = None

    if not background_bytes:
        img = Image.new("RGB", (width, height), (18, 18, 24))
        draw = ImageDraw.Draw(img)
        for y in range(height):
            ratio = y / height
            shade = int(18 + ratio * 14)
            draw.line([(0, y), (width, y)], fill=(shade, shade, shade + 4))

    draw = ImageDraw.Draw(img)

    avatar_size = 140
    avatar = _circle_avatar(avatar_bytes, avatar_size)
    avatar_pos = (50, (height - avatar_size) // 2)

    ring = Image.new("RGBA", (avatar_size + 8, avatar_size + 8), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((0, 0, avatar_size + 8, avatar_size + 8), outline=(244, 196, 48, 255), width=4)
    img.paste(ring, (avatar_pos[0] - 4, avatar_pos[1] - 4), ring)
    img.paste(avatar, avatar_pos, avatar)

    label_font = _get_font(20, bold=True)
    name_font = _get_font(38, bold=True)
    sub_font = _get_font(20)

    text_x = 230

    draw.text((text_x, 90), "NOUVEAU MEMBRE", font=label_font, fill=(244, 196, 48))
    draw.text((text_x, 125), username, font=name_font, fill=(255, 255, 255))
    draw.text((text_x, 178), f"Membre n°{member_count}", font=sub_font, fill=(160, 165, 175))

    draw.line([(text_x, 215), (text_x + 300, 215)], fill=(60, 65, 75), width=2)

    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
