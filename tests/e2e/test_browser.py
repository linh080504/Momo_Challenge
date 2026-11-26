"""Run against the local API and web with isolated demo accounts."""

import io
import os

import pytest
from PIL import Image, ImageDraw, ImageFont

WEB = os.getenv("MVP_WEB_URL")
pytestmark = pytest.mark.skipif(not WEB, reason="Set MVP_WEB_URL to run browser integration tests.")


def screenshot_fixture():
    image = Image.new("RGB", (1150, 300), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 38)
    except OSError:
        font = ImageFont.truetype("arial.ttf", 38)
    draw.multiline_text(
        (32, 26), "Tài khoản tạm giữ\nChuyển ngay qua STK 0000012374\nKhông được nói với ai",
        font=font, fill="black", spacing=17,
    )
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return {"name": "sample.png", "mimeType": "image/png", "buffer": buffer.getvalue()}


def login(page, email, password, button="Đăng nhập"):
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Mật khẩu", exact=True).fill(password)
    page.get_by_role("button", name=button, exact=True).click()


def test_mobile_screenshot_to_approved_alert():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        mobile = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        user = mobile.new_page()
        user.goto(WEB, wait_until="networkidle")
        user.get_by_label("Chọn ảnh PNG hoặc JPEG").set_input_files(screenshot_fixture())
        user.get_by_role("button", name="Kiểm tra ngay").click()
        playwright.expect(user.get_by_role("heading", name="Nguy cơ cao")).to_be_visible(timeout=20000)
        assert user.evaluate("document.documentElement.scrollWidth === innerWidth")
        user.get_by_role("button", name="Hỏi người thân").click()
        shared_link = user.get_by_label("Liên kết đã che thông tin, có hiệu lực 24 giờ")
        playwright.expect(shared_link).to_be_visible()
        shared = mobile.new_page()
        shared.goto(shared_link.input_value())
        playwright.expect(shared.get_by_role("heading", name="Kết quả được chia sẻ")).to_be_visible()
        assert "0000012374" not in shared.locator("main").inner_text()
        user.get_by_role("button", name="Báo cáo", exact=True).click()
        login(user, os.environ["MVP_BROWSER_USER_EMAIL"], os.environ["MVP_BROWSER_USER_PASSWORD"], "Đăng nhập và báo cáo")
        playwright.expect(user.get_by_role("button", name="Đã báo cáo")).to_be_visible()
        operator = browser.new_page(viewport={"width": 1280, "height": 900})
        operator.goto(WEB + "/ops", wait_until="networkidle")
        login(operator, os.environ["MVP_BROWSER_OPS_EMAIL"], os.environ["MVP_BROWSER_OPS_PASSWORD"])
        operator.get_by_role("link", name="Mạo danh cơ quan, tổ chức", exact=False).first.click()
        operator.get_by_role("button", name="Duyệt cảnh báo").click()
        playwright.expect(operator.get_by_text("Đã duyệt", exact=True)).to_be_visible()
        playwright.expect(operator.get_by_text("Duyệt bởi", exact=False)).to_be_visible()
        user.get_by_role("button", name="Kiểm tra ngay").click()
        playwright.expect(user.get_by_text("Cảnh báo đã được chuyên viên xác nhận.", exact=True)).to_be_visible(timeout=20000)
        browser.close()
