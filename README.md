# iPixel LED Matrix Python Client

Bu örnek, ESP32 üzerinde çalışan **iPixel** firmware'e WiFi üzerinden görsel göndermek için Python kütüphanesi ve demo uygulamaları içerir.

Herhangi bir yapay zeka ajanı (Claude, GPT, Gemini, Codex, GLM) bu örnekleri kullanarak LED matrix ekranlar için arayüzler oluşturabilir.



Bu örneklerde:
- ✅ 3x5 pixel bitmap font (kendi FONT dict'i)
- ✅ `draw.point()` ile piksel bazlı çizim
- ✅ Gradient text ve progress bar
- ✅ 3D efektli bar görünümü

## Gereksinimler

```bash
pip install -r requirements.txt
```

veya:

```bash
pip install Pillow requests
```

## Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `demo_display_64x16.py` | 64x16 ekran için demo |
| `demo_display_96x16.py` | 96x16 ekran için demo |
| `requirements.txt` | Python paketleri |
| `README.md` | Bu dosya |

## Kullanım

### 64x16 Ekran

```bash
python demo_display_64x16.py --ip 192.168.1.86 -i 4
```

### 96x16 Ekran

```bash
python demo_display_96x16.py --ip 192.168.1.86 -i 4
```

### Parametreler

| Parametre | Açıklama | Varsayılan |
|-----------|----------|------------|
| `--ip` | ESP32 IP adresi | `192.168.1.86` |
| `-i, --interval` | Sayfa değişim aralığı (saniye) | `4` |

## Demo Sayfaları

Demo 6 farklı sayfa gösterir:

1. **GLM** - GLM kota gösterimi (yeşil gradient)
2. **CODEX** - CODEX kota (iki bar: 5h + weekly)
3. **KIMI/GPT** - Kimi kota (mavi gradient)
4. **Weather** - Hava durumu (sıcaklık, nem, açıklama)
5. **Gemini** - Gemini kota (mor-mavi gradient)
6. **Claude** - Claude kota (turuncu gradient)

## Kendi Arayüzünü Oluştur

### Temel Kod Yapısı

```python
from PIL import Image, ImageDraw
import requests
import binascii
from io import BytesIO

WIDTH = 64   # veya 96
HEIGHT = 16

# Font ve helper fonksiyonları demo dosyasından kopyala
# FONT dict, draw_text(), draw_text_gradient(), draw_bar(), interpolate()

def send_image(host, pil_image, slot=0):
    """PNG görüntüsünü ESP32'ye gönder."""
    buf = BytesIO()
    pil_image.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    crc_val = binascii.crc32(png_bytes) & 0xFFFFFFFF
    crc_bytes = crc_val.to_bytes(4, byteorder="little")
    size_bytes = len(png_bytes).to_bytes(4, byteorder="little")

    header = bytes([0x02, 0x00, 0x00]) + size_bytes + crc_bytes + bytes([0x00, slot])
    frame = header + png_bytes
    prefix = (2 + len(frame)).to_bytes(2, byteorder="little")
    payload = prefix + frame

    url = f"http://{host}/window"
    r = requests.post(url, data=payload, timeout=4.0,
                      headers={'Content-Type': 'application/octet-stream'})
    return r.status_code == 200 and r.json().get("ok", False)

def render_my_page(data):
    """Kendi sayfanı oluştur."""
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Örnek: Başlık çiz
    draw_text_gradient(draw, "MYTITLE", 0, 1, (255, 0, 0), (0, 255, 0))
    
    # Örnek: Bar çiz
    draw_bar(draw, 0, 8, WIDTH-2, data["percent"], (100, 0, 0), (255, 0, 100))
    
    return img

# Kullanım
img = render_my_page({"percent": 75})
send_image("192.168.1.86", img)
```

### Örnek: Sistem Monitör

```python
def render_sysmon(cpu, mem, temp):
    img = Image.new("RGB", (64, 16), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # CPU bar
    draw_text(draw, "CPU", 0, 1, (0, 255, 0))
    draw_bar(draw, 20, 8, 42, cpu, (0, 100, 0), (0, 255, 0))
    
    return img
```

### Örnek: Crypto Fiyat

```python
def render_crypto(symbol, price, change):
    img = Image.new("RGB", (64, 16), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Symbol
    draw_text_gradient(draw, symbol, 0, 1, (255, 200, 0), (255, 255, 0))
    
    # Price
    price_text = f"{price:.2f}"
    draw_text(draw, price_text, 0, 9, (200, 200, 200))
    
    # Change (green/red)
    color = (0, 255, 0) if change >= 0 else (255, 0, 0)
    change_text = f"{change:+.1f}%"
    draw_text(draw, change_text, 40, 9, color)
    
    return img
```


POST request:
- URL: `http://{ESP32_IP}/window`
- Content-Type: `application/octet-stream`
- Body: `prefix + frame`

## ESP32 Gereksinimleri

- iPixel firmware kurulu ESP32 (C3, C6, S3, etc.)
- WiFi bağlı
- LED matrix ekran (HUB75 veya Wi-Fi bridge)

## AI Agent Talimatları

Yapay zeka ajanları için:

1. **Font kullan**: Demo dosyasındaki `FONT` dict'i kopyala
2. **draw.point() kullan**: `draw_text()`, `draw_text_gradient()`, `draw_bar()` fonksiyonlarını kullan
3. **WIDTH ve HEIGHT'i ayarla**: 64x16 veya 96x16
4. **send_image() fonksiyonunu kullan**: Protokol hazır
5. **Renkleri RGB tuple olarak ver**: `(255, 0, 0)` = kırmızı

## Lisans

MIT License
