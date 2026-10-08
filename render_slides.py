import asyncio, os
from playwright.async_api import async_playwright

async def main():
    html = os.path.abspath("wifi_presentation.html")
    outdir = "slides_png"; os.makedirs(outdir, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome")
        pg = await b.new_page(viewport={"width":1600,"height":900}, device_scale_factor=2)
        await pg.goto("file://"+html)
        await pg.wait_for_timeout(800)
        n = await pg.evaluate("document.querySelectorAll('section.slide').length")
        for i in range(n):
            el = pg.locator(f"section.slide >> nth={i}")
            await el.scroll_into_view_if_needed()
            await pg.wait_for_timeout(150)
            await el.screenshot(path=f"{outdir}/slide_{i+1:02d}.png")
            print("shot", i+1)
        await b.close()
        print("total slides:", n)

asyncio.run(main())
