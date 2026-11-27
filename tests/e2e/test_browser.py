"""Run against the local API and web with isolated demo accounts."""

import io
import os
import re
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

WEB = os.getenv("MVP_WEB_URL")
pytestmark = pytest.mark.skipif(not WEB, reason="Set MVP_WEB_URL to run browser integration tests.")


def screenshot_fixture(text="Tài khoản tạm giữ\nChuyển ngay qua STK 0000012374\nKhông được nói với ai"):
    image = Image.new("RGB", (1150, 300), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 38)
    except OSError:
        font = ImageFont.truetype("arial.ttf", 38)
    draw.multiline_text(
        (32, 26), text,
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
        playwright.expect(operator.get_by_text("Báo cáo trong 24 giờ", exact=True)).to_be_visible()
        operator.get_by_role("link", name="Mạo danh cơ quan, tổ chức", exact=False).first.click()
        playwright.expect(operator.get_by_role("heading", name="Bàn điều tra đa tác nhân")).to_be_visible(timeout=35000)
        graph = operator.get_by_role("group", name="Bản đồ thực thể trong chiến dịch")
        graph.get_by_role("button", name="Tài khoản đã ẩn danh", exact=False).click()
        playwright.expect(graph.get_by_role("button", name="Tài khoản đã ẩn danh", exact=False)).to_have_attribute("aria-pressed", "true")
        operator.get_by_text("Gán nhãn báo cáo", exact=True).click()
        sample = operator.locator(".ops-sample").first
        sample.get_by_label("Nhãn").select_option("scam")
        sample.get_by_role("button", name="Lưu nhãn").click()
        playwright.expect(sample.get_by_text("Lịch sử nhãn", exact=False)).to_be_visible()
        operator.get_by_role("button", name="Duyệt cảnh báo").click()
        playwright.expect(operator.get_by_text("Đã duyệt", exact=True)).to_be_visible()
        playwright.expect(operator.get_by_text("Duyệt bởi", exact=False)).to_be_visible()
        operator.get_by_text("Cảnh báo theo kênh", exact=True).click()
        playwright.expect(operator.get_by_text("Website · Đã bật cảnh báo khi kiểm tra trùng", exact=True)).to_be_visible()
        playwright.expect(operator.get_by_text("SMS · Bản xem trước", exact=True)).to_be_visible()
        user.get_by_role("button", name="Kiểm tra ngay").click()
        playwright.expect(user.get_by_text("Cảnh báo đã được chuyên viên xác nhận.", exact=True)).to_be_visible(timeout=20000)
        browser.close()


def test_desktop_receipt_and_qr_link():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(WEB, wait_until="networkidle")
        page.get_by_label("Loại tệp đính kèm").select_option("receipt")
        page.get_by_label("Chọn ảnh PNG hoặc JPEG").set_input_files(screenshot_fixture())
        page.get_by_role("button", name="Kiểm tra ngay").click()
        playwright.expect(page.locator(".receipt-preview .ocr-box").first).to_be_visible(timeout=20000)
        playwright.expect(page.get_by_text("Ảnh biên lai cần đối chiếu", exact=False)).to_be_visible()
        page.goto(WEB + "/qr", wait_until="networkidle")
        page.get_by_label("Hoặc dán nội dung QR").fill("https://example.org/")
        page.get_by_role("button", name="Kiểm tra mã", exact=True).click()
        playwright.expect(page.locator(".qr-host")).to_have_text("example.org")
        browser.close()


def test_website_report_renders_findings_and_sources():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(WEB, wait_until="networkidle")
        page.get_by_role("navigation").get_by_role("link", name="Website").click()
        page.get_by_label("Link cần kiểm tra").fill("https://example.com/?next=private-path-marker")
        page.get_by_text("Thêm bằng chứng từ ảnh hoặc tab", exact=True).click()
        page.get_by_label("Chọn ảnh PNG hoặc JPEG").set_input_files(screenshot_fixture("Đăng nhập\nMật khẩu\nOTP"))
        page.get_by_text("Thêm đoạn mã HTML có sẵn").click()
        page.get_by_label("Mã nguồn HTML").fill('<form><input type="password" value="private-field-marker"></form>')
        page.get_by_role("button", name="Phân tích website").click()
        report = page.get_by_role("region", name="Báo cáo kiểm tra website")
        playwright.expect(report.get_by_text("example.com", exact=True)).to_be_visible(timeout=20000)
        playwright.expect(report.get_by_text("Google Safe Browsing", exact=True)).to_be_visible()
        playwright.expect(report.get_by_role("heading", name="Hình ảnh website")).to_be_visible()
        playwright.expect(report.get_by_alt_text("Ảnh người dùng gửi")).to_be_visible()
        playwright.expect(report.get_by_text("HTML có trường nhập mật khẩu.", exact=True)).to_be_visible()
        playwright.expect(report.get_by_text("Ảnh có chữ liên quan đến", exact=False)).to_contain_text("mã xác thực")
        assert "private-field-marker" not in report.inner_text()
        assert "private-path-marker" not in report.inner_text()
        assert page.evaluate("document.documentElement.scrollWidth === innerWidth")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth === innerWidth")
        page.reload(wait_until="networkidle")
        page.get_by_label("Link cần kiểm tra").fill("https://www.kaspersky.com.vn/resource-center/")
        page.get_by_role("button", name="Phân tích website").click()
        playwright.expect(page.get_by_role("heading", name=re.compile(r"^Cần xác minh(?: nội dung trang)?$"))).to_be_visible(timeout=20000)
        playwright.expect(page.get_by_text("Khớp tên miền chính thức của Kaspersky", exact=True)).to_be_visible()
        playwright.expect(page.locator(".result-score")).to_have_count(0)
        browser.close()


def test_team_prototype_can_use_the_integrated_api():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page()
        page.goto(WEB + "/prototype", wait_until="networkidle")
        page.get_by_role("textbox").fill("Tài khoản tạm giữ. Chuyển ngay qua STK 0000007421, không được nói với ai.")
        with page.expect_response(lambda response: response.url.endswith("/v1/analyze/stream")) as result:
            page.get_by_role("button", name="Kiểm tra", exact=True).click()
        assert result.value.status == 200
        playwright.expect(page.get_by_role("heading", name="NGUY CƠ CAO", exact=True)).to_be_visible(timeout=20000)
        browser.close()


@pytest.mark.skipif(not os.getenv("MVP_BROWSER_AUDIO_FIXTURE"), reason="Requires configured Whisper and a WAV fixture.")
def test_mobile_speech_reaches_analysis_result():
    playwright = pytest.importorskip("playwright.sync_api")
    fixture = Path(os.environ["MVP_BROWSER_AUDIO_FIXTURE"]).resolve(strict=True)
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        page.goto(WEB, wait_until="networkidle")
        page.get_by_label("Loại tệp đính kèm").select_option("audio")
        page.get_by_label("Chọn tệp ghi âm").set_input_files(fixture)
        page.get_by_role("button", name="Kiểm tra ngay").click()
        playwright.expect(page.get_by_role("region", name="Kết quả phân tích")).to_be_visible(timeout=35000)
        assert page.evaluate("document.documentElement.scrollWidth === innerWidth")
        browser.close()
