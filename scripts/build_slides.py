"""Build slides.html from scripts/slides_template.html, embedding screenshots as base64 JPEG.
Run: python scripts/build_slides.py   (needs macOS `sips`, or Pillow as fallback)"""
import base64
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jpeg_b64(name, tmp):
    src = ROOT / "screenshots" / f"{name}.png"
    out = Path(tmp) / f"{name}.jpg"
    try:
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "80", str(src), "--out", str(out)], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        from PIL import Image
        Image.open(src).convert("RGB").save(out, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(out.read_bytes()).decode()


def build(template="slides_template.html", target="slides.html"):
    html = (ROOT / "scripts" / template).read_text()
    with tempfile.TemporaryDirectory() as tmp:
        cache = {}
        html = re.sub(r"\{\{IMG:([\w-]+)\}\}", lambda m: cache.setdefault(m.group(1), jpeg_b64(m.group(1), tmp)), html)
    (ROOT / target).write_text(html)
    print(f"wrote {target}: {(ROOT / target).stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    build()
