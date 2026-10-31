"""Capture the website screenshots that scroll inside the project cards.

    pip install playwright pillow && python -m playwright install chromium
    python3 scripts/capture_frames.py            # every frame in content.PROJECTS
    python3 scripts/capture_frames.py kodex      # only the projects whose key matches

Each frame is a 1280x720 viewport, downscaled to 720x405 JPEG in scripts/frames/.
Cookie banners and one-time popups are removed from the page before the shot,
without clicking accept, so no consent is given on anyone's behalf.
"""
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import content as C  # noqa: E402

FRAMES = Path(__file__).resolve().parent / "frames"
VIEWPORT = {"width": 1280, "height": 720}
OUT_SIZE = (720, 405)

REMOVE_OVERLAYS = r"""
() => {
  const pattern = /cookie|consent|adsense|personalis|personaliz|note from|author's note|newsletter/i;
  let removed = 0;
  for (const el of Array.from(document.querySelectorAll('body *'))) {
    if (!el.isConnected) continue;
    const cs = getComputedStyle(el);
    if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;
    const r = el.getBoundingClientRect();
    if (r.height > innerHeight * 0.9 && r.width > innerWidth * 0.9 && !pattern.test(el.innerText || '')) continue;
    const dialog = el.getAttribute('role') === 'dialog' || el.getAttribute('aria-modal') === 'true';
    if (dialog || pattern.test(el.innerText || '')) { el.remove(); removed++; }
  }
  document.documentElement.style.overflow = '';
  document.body.style.overflow = '';
  return removed;
}
"""


def shoot(page, frame):
    page.goto(frame["url"], wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:  # noqa: BLE001 - some sites keep a socket open; the timeout is fine
        pass
    page.wait_for_timeout(3000)
    page.evaluate(REMOVE_OVERLAYS)
    if frame.get("click"):
        page.get_by_role("button", name=frame["click"], exact=True).first.click(timeout=10000)
    if frame.get("scroll"):
        page.evaluate("y => window.scrollTo({top: y, behavior: 'instant'})", frame["scroll"])
    page.wait_for_timeout(frame.get("wait_after", 1200))
    page.evaluate(REMOVE_OVERLAYS)
    png = page.screenshot(type="png")
    img = Image.open(io.BytesIO(png)).convert("RGB").resize(OUT_SIZE, Image.LANCZOS)
    out = FRAMES / f"{frame['shot']}.jpg"
    img.save(out, "JPEG", quality=74, optimize=True, progressive=True, subsampling=2)
    return out


def main():
    only = sys.argv[1:]
    FRAMES.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        for project in C.PROJECTS:
            if only and project["key"] not in only:
                continue
            for frame in project["frames"]:
                ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1, color_scheme="light")
                page = ctx.new_page()
                try:
                    out = shoot(page, frame)
                    print(f"ok   {out.name:<16} {out.stat().st_size // 1024:>4} KB  {frame['url']}")
                except Exception as e:  # noqa: BLE001
                    print(f"FAIL {frame['shot']:<16} {frame['url']}: {e}")
                ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
