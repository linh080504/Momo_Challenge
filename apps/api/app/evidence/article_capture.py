import base64
from threading import BoundedSemaphore


CAPTURES = BoundedSemaphore(2)
VIEWPORT = {"width": 1440, "height": 810}
MAX_CAPTURE_BYTES = 300_000


def capture_article(html, url, assets, *, offline=False):
    """Capture the rendered page in a read-only Chromium tab."""
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError:
        return {}

    if not CAPTURES.acquire(blocking=False):
        return {}
    capture = {}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(chromium_sandbox=True, timeout=4000)
            try:
                context = browser.new_context(java_script_enabled=False, service_workers="block",
                                              accept_downloads=False, offline=offline, viewport=VIEWPORT)
                page = context.new_page()
                served = False

                def serve(route):
                    nonlocal served
                    request = route.request
                    if request.method != "GET":
                        route.abort()
                    elif not served and request.url == url and request.resource_type == "document" and request.frame == page.main_frame:
                        served = True
                        route.fulfill(status=200, body=html, content_type="text/html; charset=utf-8", headers={
                            "content-security-policy": "default-src 'none'; style-src 'unsafe-inline' https:; img-src https: data:; font-src https:; base-uri 'none'; form-action 'none'",
                        })
                    elif offline and request.url in assets and assets[request.url][0] == request.resource_type:
                        _, content_type, body = assets[request.url]
                        headers = {"access-control-allow-origin": "*"} if request.resource_type == "font" else None
                        route.fulfill(status=200, body=body, content_type=content_type, headers=headers)
                    elif not offline and assets.get(request.url) == request.resource_type:
                        try:
                            asset = route.fetch(max_redirects=0, timeout=2000)
                            if asset.ok:
                                route.fulfill(response=asset)
                            else:
                                route.abort()
                        except Error:
                            route.abort()
                    else:
                        route.abort()

                context.route("**/*", serve)
                page.goto(url, wait_until="load", timeout=6000)
                height = page.evaluate("Math.max(document.documentElement.scrollHeight, document.body?.scrollHeight ?? 0)")
                if height > VIEWPORT["height"]:
                    clip = {"x": 0, "y": 0, "width": VIEWPORT["width"],
                            "height": min(height, VIEWPORT["height"] * 3)}
                    try:
                        frame = page.screenshot(type="jpeg", quality=62, full_page=True, clip=clip, timeout=2500)
                        if len(frame) <= MAX_CAPTURE_BYTES:
                            return {"capture_jpeg": base64.b64encode(frame).decode("ascii")}
                    except Error:
                        pass
                frame = page.screenshot(type="jpeg", quality=76, timeout=2500)
                if len(frame) <= MAX_CAPTURE_BYTES:
                    capture["capture_jpeg"] = base64.b64encode(frame).decode("ascii")
            finally:
                browser.close()
    except (Error, OSError):
        pass
    finally:
        CAPTURES.release()
    return capture
