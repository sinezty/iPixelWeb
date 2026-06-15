#!/usr/bin/env python3
"""
iPixel LED Matrix Display Demo - 96x16
======================================

Bu örnek, ESP32 üzerinde çalışan iPixel firmware'e WiFi üzerinden
PNG görüntüleri gönderir.

Önemli: LED matrix ekranlarda PIL draw.rectangle() ve font fonksiyonları
yanlış çalışır. Her pikseli draw.point() ile tek tek çizmek gerekir.

Kullanım:
    python demo_display_96x16.py --ip 192.168.1.86 -i 4

Detaylar için README.md dosyasına bakın.
"""

import time
import random
import argparse
import requests
import binascii
import datetime
from io import BytesIO
from PIL import Image, ImageDraw

TIMEOUT = 4.0
WIDTH = 96
HEIGHT = 16

# =========================================================
# FONT - 3x5 pixel bitmap font
# =========================================================
FONT = {
    '0': [7,5,5,5,7], '1': [4,4,4,4,4], '2': [7,1,7,4,7],
    '3': [7,1,7,1,7], '4': [5,5,7,1,1], '5': [7,4,7,1,7],
    '6': [7,4,7,5,7], '7': [7,1,1,1,1], '8': [7,5,7,5,7],
    '9': [7,5,7,1,7], ':': [0,4,0,4,0], '.': [0,0,0,0,4],
    '%': [5,1,2,4,5], 'C': [7,4,4,4,7], 'D': [6,5,5,5,6],
    'P': [6,5,6,4,4], 'E': [7,4,6,4,7], 'G': [7,4,5,5,7],
    'L': [4,4,4,4,7], 'M': [5,7,5,5,5], 'N': [5,6,5,5,5],
    'O': [7,5,5,5,7], 'R': [6,5,6,5,5], 'T': [7,2,2,2,2],
    'W': [5,5,5,7,5], 'X': [5,5,2,5,5], 'A': [2,5,7,5,5],
    ' ': [0,0,0,0,0], 'H': [5,5,7,5,5], '-': [0,0,7,0,0],
    'I': [7,2,2,2,7], 'K': [5,5,6,5,5], 'S': [7,4,7,1,7],
    'U': [5,5,5,5,7], 'V': [5,5,5,5,2], 'Y': [5,5,2,2,2],
    'Z': [7,1,2,4,7], '°': [4,0,0,0,0],
}

# =========================================================
# HELPERS
# =========================================================
def turkish_to_english(text):
    mapping = {
        'Ç': 'C', 'Ğ': 'G', 'İ': 'I', 'I': 'I', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U',
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u'
    }
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text

def text_width(text):
    text = turkish_to_english(text)
    w = 0
    for ch in text.upper():
        if ch in ['.', ':', '1', '°']:
            w += 2
        else:
            w += 4
    return w

def draw_text(draw, text, x, y, color):
    """Draw text using bitmap font - pixel by pixel."""
    text = turkish_to_english(text)
    cx = x
    for ch in text.upper():
        glyph = FONT.get(ch)
        if not glyph:
            cx += 2 if ch in ['.', ':', '1', '°'] else 4
            continue
        for ry, row in enumerate(glyph):
            for rx in range(3):
                if (row >> (2 - rx)) & 1:
                    draw.point((cx + rx, y + ry), fill=color)
        cx += 2 if ch in ['.', ':', '1', '°'] else 4

def draw_text_gradient(draw, text, x, y, c1, c2, direction="horizontal"):
    """Draw text with gradient - pixel by pixel."""
    text = turkish_to_english(text)
    cx = x
    w = text_width(text)
    for ch in text.upper():
        glyph = FONT.get(ch)
        if not glyph:
            cx += 2 if ch in ['.', ':', '1', '°'] else 4
            continue
        for ry, row in enumerate(glyph):
            for rx in range(3):
                if (row >> (2 - rx)) & 1:
                    px = cx + rx
                    py = y + ry
                    if direction == "vertical":
                        t = ry / 4.0
                    else:
                        t = (px - x) / max(w, 1)
                    color = interpolate(c1, c2, t)
                    draw.point((px, py), fill=color)
        cx += 2 if ch in ['.', ':', '1', '°'] else 4

def interpolate(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def draw_bar(draw, x, y, w, percent, c1, c2, show_percent=True):
    """Draw progress bar - pixel by pixel."""
    empty = (12, 12, 12)
    frame = (40, 40, 40)
    
    # Frame top and bottom
    for i in range(w + 2):
        draw.point((x + i, y), fill=frame)
        draw.point((x + i, y + 6), fill=frame)
    
    # Frame sides
    for h in range(1, 6):
        draw.point((x, y + h), fill=frame)
        draw.point((x + w + 1, y + h), fill=frame)
    
    fill_w = int(w * percent / 100)
    
    # Fill bar
    for i in range(1, w + 1):
        if i <= fill_w:
            t = i / max(fill_w, 1)
            base_color = interpolate(c1, c2, t)
        else:
            base_color = empty
        
        for h in range(1, 6):
            # 3D effect
            if h == 1 or h == 5:
                shade = 0.5
            elif h == 2 or h == 4:
                shade = 0.8
            else:
                shade = 1.0
            color = tuple(int(c * shade) for c in base_color)
            draw.point((x + i, y + h), fill=color)
    
    # Percent text
    if show_percent:
        label = f"{int(percent)}%"
        tx = x + 1 + (w - text_width(label)) // 2
        ty = y + 1
        text_color = (0, 0, 0) if percent > 50 else (255, 255, 255)
        draw_text(draw, label, tx, ty, text_color)

# =========================================================
# SEND IMAGE
# =========================================================
def send_image(host, pil_image, slot=0):
    """
    PNG görüntüsünü ESP32'ye gönder.
    
    Args:
        host: ESP32 IP adresi (örn: "192.168.1.86")
        pil_image: PIL Image nesnesi (RGB, WIDTH x HEIGHT)
        slot: Görüntü slot'u (0-9, varsayılan 0)
    
    Returns:
        bool: Başarılı ise True
    """
    buf = BytesIO()
    pil_image.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    # iPixel protokolü
    crc_val = binascii.crc32(png_bytes) & 0xFFFFFFFF
    crc_bytes = crc_val.to_bytes(4, byteorder="little")
    size_bytes = len(png_bytes).to_bytes(4, byteorder="little")

    header = bytes([0x02, 0x00, 0x00]) + size_bytes + crc_bytes + bytes([0x00, slot])
    frame = header + png_bytes
    prefix = (2 + len(frame)).to_bytes(2, byteorder="little")
    payload = prefix + frame

    url = f"http://{host}/window"
    r = requests.post(url, data=payload, timeout=TIMEOUT,
                      headers={'Content-Type': 'application/octet-stream'})
    return r.status_code == 200 and r.json().get("ok", False)

# =========================================================
# RENDER FUNCTIONS
# =========================================================
def render_glm(data):
    """GLM kota sayfası."""
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    d = ImageDraw.Draw(img)
    
    time_str = datetime.datetime.now().strftime("%H:%M")
    percent = data.get("percent", 0)
    reset = data.get("reset", "--")
    
    draw_text_gradient(d, "GLM5.1", 0, 1, (0, 255, 120), (0, 255, 255))
    draw_text_gradient(d, time_str, WIDTH - text_width(time_str), 1, (255, 80, 0), (255, 180, 0))
    draw_text(d, reset, (WIDTH - text_width(reset)) // 2, 1, (200, 200, 200))
    draw_bar(d, 0, 8, 94, percent, (0, 130, 30), (0, 255, 100))
    
    return img

def render_codex(data):
    """CODEX kota sayfası - iki bar."""
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    d = ImageDraw.Draw(img)
    
    time_str = datetime.datetime.now().strftime("%H:%M")
    p5 = data.get("p5", 0)
    pw = data.get("pw", 0)
    reset = data.get("reset", "--")
    
    draw_text_gradient(d, "CODEX", 0, 1, (255, 0, 180), (160, 0, 255))
    draw_text_gradient(d, time_str, WIDTH - text_width(time_str), 1, (255, 80, 0), (255, 180, 0))
    draw_text(d, reset, (WIDTH - text_width(reset)) // 2, 1, (200, 200, 200))
    
    draw_bar(d, 0, 8, 45, p5, (120, 0, 120), (255, 0, 150))
    draw_bar(d, 49, 8, 45, pw, (150, 30, 0), (255, 110, 0))
    
    return img

def render_gpt(data):
    """GPT/Kimi kota sayfası."""
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    d = ImageDraw.Draw(img)
    
    time_str = datetime.datetime.now().strftime("%H:%M")
    percent = data.get("percent", 0)
    reset = data.get("reset", "--")
    
    draw_text_gradient(d, "KIMI", 0, 1, (0, 150, 255), (0, 255, 255))
    draw_text_gradient(d, time_str, WIDTH - text_width(time_str), 1, (255, 80, 0), (255, 180, 0))
    draw_text(d, reset, (WIDTH - text_width(reset)) // 2, 1, (200, 200, 200))
    draw_bar(d, 0, 8, 94, percent, (0, 80, 180), (0, 210, 255))
    
    return img

def render_weather(data):
    """Hava durumu sayfası."""
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    d = ImageDraw.Draw(img)
    
    temp = data.get("temp", 0)
    feels = data.get("feels", 0)
    hum = data.get("hum", 0)
    desc = data.get("desc", "CLEAR")
    
    # Separator line
    for y in range(16):
        d.point((16, y), fill=(35, 35, 35))
    
    temp_text = f"{temp}C"
    draw_text_gradient(d, temp_text, 18, 1, (255, 140, 0), (255, 200, 0))
    
    feels_text = f"HIS:{feels}C"
    draw_text_gradient(d, feels_text, 38, 1, (255, 80, 0), (255, 180, 0))
    
    hum_text = f"{hum}%"
    draw_text_gradient(d, hum_text, WIDTH - text_width(hum_text), 1, (0, 255, 180), (0, 180, 255))
    
    desc_w = text_width(desc)
    desc_x = 18 + (78 - desc_w) // 2
    draw_text(d, desc, desc_x, 9, (200, 200, 200))
    
    return img

def render_gemini(data):
    """Gemini kota sayfası."""
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    d = ImageDraw.Draw(img)
    
    time_str = datetime.datetime.now().strftime("%H:%M")
    percent = data.get("percent", 0)
    reset = data.get("reset", "--")
    
    draw_text_gradient(d, "GEMINI", 0, 1, (122, 34, 255), (0, 210, 255))
    draw_text_gradient(d, time_str, WIDTH - text_width(time_str), 1, (255, 80, 0), (255, 180, 0))
    draw_text(d, reset, (WIDTH - text_width(reset)) // 2, 1, (200, 200, 200))
    draw_bar(d, 0, 8, 94, percent, (58, 13, 189), (0, 180, 255))
    
    return img

def render_claude(data):
    """Claude kota sayfası."""
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    d = ImageDraw.Draw(img)
    
    time_str = datetime.datetime.now().strftime("%H:%M")
    percent = data.get("percent", 0)
    reset = data.get("reset", "--")
    
    draw_text_gradient(d, "CLAUDE", 0, 1, (255, 107, 74), (238, 205, 163))
    draw_text_gradient(d, time_str, WIDTH - text_width(time_str), 1, (255, 80, 0), (255, 180, 0))
    draw_text(d, reset, (WIDTH - text_width(reset)) // 2, 1, (200, 200, 200))
    draw_bar(d, 0, 8, 94, percent, (179, 57, 37), (233, 154, 119))
    
    return img

# =========================================================
# MAIN
# =========================================================
RENDERERS = {
    "glm": render_glm,
    "codex": render_codex,
    "gpt": render_gpt,
    "weather": render_weather,
    "gemini": render_gemini,
    "claude": render_claude,
}

def get_data(page):
    """Demo için rastgele veri üret."""
    if page == "glm":
        return {"percent": random.randint(10, 95), "reset": f"{random.randint(1,59)}m"}
    elif page == "codex":
        return {"p5": random.randint(10, 90), "pw": random.randint(20, 95), "reset": f"{random.randint(1,59)}m"}
    elif page == "gpt":
        return {"percent": random.randint(15, 85), "reset": f"{random.randint(1,30)}d"}
    elif page == "weather":
        descs = ["GUNESLI", "BULUTLU", "PARCALI", "YAGMURLU", "SISLI"]
        return {"temp": random.randint(10, 35), "feels": random.randint(8, 33), "hum": random.randint(30, 90), "desc": random.choice(descs)}
    elif page == "gemini":
        return {"percent": random.randint(5, 98), "reset": f"{random.randint(1,59)}m"}
    elif page == "claude":
        return {"percent": random.randint(10, 90), "reset": f"{random.randint(1,59)}m"}

def main():
    parser = argparse.ArgumentParser(description="iPixel LED Matrix Demo - 96x16")
    parser.add_argument("--ip", default="192.168.1.86", help="ESP32 IP adresi")
    parser.add_argument("-i", "--interval", type=int, default=4, help="Sayfa değişim aralığı (saniye)")
    args = parser.parse_args()

    pages = list(RENDERERS.keys())

    print(f"iPixel LED Matrix Demo")
    print(f"Ekran: {WIDTH}x{HEIGHT}")
    print(f"ESP32: {args.ip}")
    print("Ctrl+C ile cikis\n")

    idx = 0
    try:
        while True:
            page = pages[idx]
            data = get_data(page)
            img = RENDERERS[page](data)

            clock = time.strftime("%H:%M:%S")
            print(f"[{clock}] {page.upper():8}", end=" ")
            if page == "codex":
                print(f"5h:{data['p5']}% wk:{data['pw']}%", end="")
            elif page == "weather":
                print(f"{data['temp']}C {data['hum']}%", end="")
            else:
                print(f"{data['percent']}%", end="")
            print(" >> OK" if send_image(args.ip, img) else " >> HATA")

            idx = (idx + 1) % len(pages)
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nDurduruldu.")

if __name__ == "__main__":
    main()