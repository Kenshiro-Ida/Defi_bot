"""Fill the AIDEFI Deposit.png template with amount, user address and tx hash."""
import io
import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "assets", "Deposit.png")
FONT_MONO = os.path.join(BASE_DIR, "fonts", "Consolas-Bold.ttf")
FONT_SANS = os.path.join(BASE_DIR, "fonts", "Arial-Bold.ttf")

# Dashed-box geometry measured from the 1254x1254 template.
# Each box: left border ~434, right border ~942. Interior padding applied below.
BOX_LEFT = 434
BOX_RIGHT = 942
PAD_X = 26  # left padding inside the box

# Vertical center of each dashed box.
FIELDS = {
    "amount": 594,
    "address": 732,
    "hash": 863,
}

TEXT_COLOR = (255, 255, 255)


def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _fit_font(draw, text, font_path, start_size, max_width):
    """Return a font sized so `text` fits within max_width (shrinking if needed)."""
    size = start_size
    while size > 12:
        font = _load_font(font_path, size)
        w = draw.textlength(text, font=font)
        if w <= max_width:
            return font
        size -= 2
    return _load_font(font_path, 12)


def _draw_centered_v(draw, text, font, x, center_y, color):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_h = bbox[3] - bbox[1]
    y = center_y - text_h / 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=color)


def fill_deposit_image(amount, user_address, tx_hash):
    """Return filled PNG image as bytes."""
    img = Image.open(TEMPLATE_PATH).convert("RGB")
    draw = ImageDraw.Draw(img)

    max_width = BOX_RIGHT - BOX_LEFT - 2 * PAD_X
    x = BOX_LEFT + PAD_X

    amount_str = str(amount)
    addr_str = str(user_address)
    hash_str = str(tx_hash)

    # Amount: sans-serif bold, larger. Address & hash: monospace, auto-fit.
    amount_font = _fit_font(draw, amount_str, FONT_SANS, 44, max_width)
    addr_font = _fit_font(draw, addr_str, FONT_MONO, 34, max_width)
    hash_font = _fit_font(draw, hash_str, FONT_MONO, 34, max_width)

    _draw_centered_v(draw, amount_str, amount_font, x, FIELDS["amount"], TEXT_COLOR)
    _draw_centered_v(draw, addr_str, addr_font, x, FIELDS["address"], TEXT_COLOR)
    _draw_centered_v(draw, hash_str, hash_font, x, FIELDS["hash"], TEXT_COLOR)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


if __name__ == "__main__":
    data = fill_deposit_image(
        "1,500 USDT",
        "0x65bb8da590f0C049c632f1743942734A39aBbe5F",
        "0x9f2c1a4b7e8d3f6a0c5b2e9d1f4a7c8b3e6d9f2a1c4b7e8d3f6a0c5b2e9d1f4a",
    )
    with open(os.path.join(BASE_DIR, "_preview.png"), "wb") as f:
        f.write(data)
    print("wrote preview", len(data), "bytes")
