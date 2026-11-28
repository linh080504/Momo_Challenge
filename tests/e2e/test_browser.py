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
        user.get_by_role("tab", name="Ảnh chụp").click()
        screenshot = user.get_by_role("tabpanel", name="Ảnh chụp")
        screenshot.get_by_label("Chọn ảnh PNG hoặc JPEG").set_input_files(screenshot_fixture())
        with user.expect_request("**/v1/analyze/stream") as analysis_request:
            screenshot.get_by_role("button", name="Kiểm tra ngay", exact=True).click()
        assert analysis_request.value.post_data_json["qwen_vision"] is True
        playwright.expect(user).to_have_url(WEB + "/website")
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
        operator.get_by_text("Cấu hình hệ thống", exact=True).click()
        playwright.expect(operator.get_by_text("Phiên âm Whisper", exact=True)).to_be_visible()
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
        user.get_by_role("button", name="Kiểm tra ngay", exact=True).click()
        playwright.expect(user.get_by_text("Cảnh báo đã được chuyên viên xác nhận.", exact=True)).to_be_visible(timeout=20000)
        browser.close()


def test_desktop_receipt_and_qr_link():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(WEB, wait_until="networkidle")
        page.get_by_role("tab", name="Biên lai").click()
        page.get_by_role("tabpanel", name="Biên lai").get_by_label("Chọn ảnh PNG hoặc JPEG").set_input_files(screenshot_fixture())
        page.get_by_role("button", name="Kiểm tra ngay").click()
        playwright.expect(page).to_have_url(WEB + "/website")
        playwright.expect(page.locator(".receipt-preview .ocr-box").first).to_be_visible(timeout=20000)
        playwright.expect(page.get_by_text("Ảnh biên lai cần đối chiếu", exact=False)).to_be_visible()
        page.goto(WEB + "/qr", wait_until="networkidle")
        page.get_by_label("Hoặc dán nội dung QR").fill("https://example.org/")
        page.get_by_role("button", name="Kiểm tra mã", exact=True).click()
        playwright.expect(page.locator(".qr-host")).to_have_text("example.org")
        browser.close()


def test_brand_ops_demo_publishes_and_revokes_exact_qr_warning():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        operator = browser.new_page(viewport={"width": 1280, "height": 900})
        operator.goto(WEB + "/ops", wait_until="networkidle")
        login(operator, os.environ["MVP_BROWSER_OPS_EMAIL"], os.environ["MVP_BROWSER_OPS_PASSWORD"])
        operator.get_by_text("Phát hiện website mạo danh MoMo", exact=True).click()
        operator.get_by_text("Nhập ứng viên", exact=True).click()
        operator.get_by_role("button", name="Dùng tên miền mẫu").click()
        operator.get_by_role("button", name="Thêm vào hàng duyệt").click()
        host = operator.get_by_role("heading", name="momo-hoan-tien.example")
        playwright.expect(host).to_be_visible()
        card = operator.locator(".brand-queue article").filter(has=host)
        playwright.expect(card.get_by_text("Cần xác minh", exact=False)).to_be_visible()
        card.get_by_text("Đối chiếu HTML đã thu thập").click()
        card.get_by_role("button", name="Dùng dữ liệu giả lập").click()
        card.get_by_role("button", name="Đối chiếu bằng chứng").click()
        card.get_by_role("button", name="Duyệt cảnh báo MoMo").click()
        playwright.expect(host).to_have_count(0)

        user = browser.new_page(viewport={"width": 390, "height": 844})
        user.goto(WEB + "/qr", wait_until="networkidle")
        link = user.get_by_label("Hoặc dán nội dung QR")
        check = user.get_by_role("button", name="Kiểm tra mã", exact=True)
        warning = user.get_by_text("Chuyên viên PayPause đã xác nhận website mạo danh MoMo.")
        link.fill("https://momo-hoan-tien.example/")
        check.click()
        playwright.expect(warning).to_be_visible()
        assert user.evaluate("document.documentElement.scrollWidth === innerWidth")

        operator.get_by_label("Trạng thái hồ sơ").select_option("approved")
        with operator.expect_download() as download:
            card.get_by_role("button", name="Xuất hồ sơ").click()
        assert download.value.suggested_filename == "momo-hoan-tien.example.json"
        card.get_by_role("button", name="Rút cảnh báo").click()
        playwright.expect(host).to_have_count(0)
        check.click()
        playwright.expect(user.get_by_role("heading", name="QR liên kết")).to_be_visible()
        playwright.expect(warning).to_have_count(0)
        browser.close()


def test_transfer_confirmation_distinguishes_mismatch_payment_and_unreadable_qr():
    import qrcode

    from app.kit import vietqr

    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(WEB, wait_until="networkidle")
        page.get_by_role("link", name="Đang chờ nhận tiền? Kiểm tra mã QR").click()
        playwright.expect(page).to_have_url(WEB + "/truoc-khi-xac-nhan")
        page.get_by_role("button", name="Thử tình huống hoàn tiền").click()
        check = page.get_by_role("button", name="Kiểm tra ngay", exact=True)
        check.click()
        playwright.expect(page.get_by_text("Nếu xác nhận, bạn sẽ chuyển đi 500.000 ₫.")).to_be_visible(timeout=20000)
        page.get_by_text("Dừng để xác minh", exact=True).click()
        playwright.expect(page.get_by_role("link", name="Mở Trợ giúp MoMo")).to_have_attribute("href", "https://www.momo.vn/hoi-dap")
        playwright.expect(page.get_by_role("button", name="Báo cáo cho PayPause")).to_have_count(0)
        page.get_by_role("button", name="Hỏi người thân").click()
        playwright.expect(page.get_by_role("heading", name="Người thân sẽ thấy")).to_be_visible()
        summary = page.get_by_label("Liên kết đã che thông tin, có hiệu lực 24 giờ")
        shared = browser.new_page()
        shared.goto(summary.input_value())
        playwright.expect(shared.get_by_text("Người gửi đang chờ nhận tiền nhưng mã QR yêu cầu chuyển tiền đi.", exact=False)).to_be_visible()
        assert "500.000" not in shared.locator("main").inner_text()
        assert page.evaluate("document.documentElement.scrollWidth === innerWidth")

        image = qrcode.make(vietqr.build("970436", "0000048755", 50000)).get_image().convert("RGB")
        for name, picture, heading in (
            ("payment.png", image, "Đây là mã chuyển tiền đi"),
            ("blank.png", Image.new("RGB", (150, 150), "white"), "Cần xác minh mã QR"),
        ):
            buffer = io.BytesIO()
            picture.save(buffer, "PNG")
            page.get_by_label("Chọn ảnh PNG hoặc JPEG").set_input_files({"name": name, "mimeType": "image/png", "buffer": buffer.getvalue()})
            page.get_by_role("radio", name="Tôi đang trả tiền").check()
            check.click()
            playwright.expect(page.get_by_role("heading", name=heading)).to_be_visible(timeout=30000)
            if name == "payment.png":
                playwright.expect(page.get_by_text("Dừng để xác minh", exact=True)).to_have_count(0)
        browser.close()


def test_home_checker_shows_six_modes_and_opens_qr_result_on_website_page():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(WEB, wait_until="networkidle")
        checker = page.get_by_role("region", name="Kiểm tra ngay", exact=True)
        tabs = checker.get_by_role("tab")
        playwright.expect(tabs).to_have_count(6)
        website = checker.get_by_role("tab", name="Website", exact=True)
        url = checker.get_by_label("Link cần kiểm tra")
        intro = page.locator(".landing-hero-copy")
        playwright.expect(intro.get_by_role("heading", name="PayPause AI")).to_be_visible()
        call_to_action = intro.locator(".landing-hero-actions")
        actions_box = call_to_action.bounding_box()
        checker_box = intro.get_by_role("region", name="Kiểm tra ngay", exact=True).bounding_box()
        assert 0 < checker_box["y"] - actions_box["y"] - actions_box["height"] < 40
        url.fill("https://example.org/")
        website.press("ArrowRight")
        playwright.expect(checker.get_by_role("tab", name="Tin nhắn", exact=True)).to_have_attribute("aria-selected", "true")
        website.click()
        playwright.expect(url).to_have_value("https://example.org/")
        checker.get_by_role("tab", name="Mã QR", exact=True).click()
        playwright.expect(checker.get_by_role("tab", name="Mã QR", exact=True)).to_have_attribute("aria-selected", "true")
        checker.get_by_label("Hoặc dán nội dung QR").fill("https://example.org/")
        checker.get_by_role("button", name="Kiểm tra mã", exact=True).click()
        playwright.expect(page).to_have_url(WEB + "/website")
        playwright.expect(checker).to_have_count(0)
        playwright.expect(page.get_by_role("tab", name="Mã QR", exact=True)).to_have_attribute("aria-selected", "true")
        playwright.expect(page.locator(".qr-host")).to_have_text("example.org")
        assert page.evaluate("document.documentElement.scrollWidth === innerWidth")
        browser.close()


def test_website_menu_and_home_check_links_open_the_shared_tabs():
    playwright = pytest.importorskip("playwright.sync_api")
    selectors = (".landing-menu a[href='/website']", ".landing-nav-cta", ".landing-hero-actions .primary")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        for selector in selectors:
            page.goto(WEB, wait_until="networkidle")
            page.locator(selector).click()
            playwright.expect(page).to_have_url(WEB + "/website")
            playwright.expect(page.get_by_role("tab")).to_have_count(6)
            playwright.expect(page.get_by_role("tab", name="Website", exact=True)).to_have_attribute("aria-selected", "true")
        page.goto(WEB, wait_until="networkidle")
        page.get_by_role("link", name="Tải ảnh để kiểm tra").click()
        playwright.expect(page).to_have_url(WEB + "/website#kiem-tra-image")
        playwright.expect(page.get_by_role("tabpanel", name="Ảnh chụp")).to_be_visible()
        browser.close()


@pytest.mark.parametrize(("tab", "label", "entry", "button", "request_key"), [
    ("Website", "Link cần kiểm tra", "https://example.org/", "Phân tích website", "url"),
    ("Tin nhắn", "Tin nhắn cần kiểm tra", "Hãy chuyển ngay vào tài khoản tạm giữ để xác minh.", "Kiểm tra ngay", "text"),
])
def test_home_submits_text_and_website_checks_after_navigation(tab, label, entry, button, request_key):
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page()
        page.goto(WEB, wait_until="networkidle")
        page.get_by_role("tab", name=tab, exact=True).click()
        panel = page.get_by_role("tabpanel", name=tab, exact=True)
        panel.get_by_label(label).fill(entry)
        with page.expect_request("**/v1/analyze/stream") as request:
            panel.get_by_role("button", name=button, exact=True).click()
        playwright.expect(page).to_have_url(WEB + "/website")
        playwright.expect(page.get_by_role("tab", name=tab, exact=True)).to_have_attribute("aria-selected", "true")
        assert request.value.post_data_json[request_key] == entry
        playwright.expect(page.get_by_role("region", name="Kết quả phân tích")).to_be_visible(timeout=45000)
        playwright.expect(page.locator(".home-checker")).to_have_count(0)
        browser.close()


def test_website_report_renders_findings_and_sources():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(WEB, wait_until="networkidle")
        page.get_by_role("navigation").get_by_role("link", name="Website").click()
        playwright.expect(page.get_by_role("heading", name="Kiểm tra nội dung đáng ngờ")).to_be_visible()
        page.get_by_label("Link cần kiểm tra").fill("https://example.com/?next=private-path-marker")
        page.get_by_text("Thêm bằng chứng từ ảnh hoặc tab", exact=True).click()
        page.get_by_role("tabpanel", name="Website").get_by_label("Chọn ảnh PNG hoặc JPEG").set_input_files(
            screenshot_fixture("Đăng nhập\nMật khẩu\nOTP")
        )
        page.get_by_text("Thêm đoạn mã HTML có sẵn").click()
        page.get_by_label("Mã nguồn HTML").fill('<form><input type="password" value="private-field-marker"></form>')
        page.get_by_role("button", name="Phân tích website").click()
        report = page.get_by_role("region", name="Báo cáo kiểm tra website")
        playwright.expect(report.get_by_text("example.com", exact=True)).to_be_visible(timeout=20000)
        playwright.expect(report.get_by_text("Google Safe Browsing", exact=True)).to_be_visible()
        playwright.expect(report.get_by_role("heading", name="Hình ảnh website")).to_be_visible()
        playwright.expect(report.get_by_alt_text("Ảnh người dùng gửi")).to_be_visible()
        playwright.expect(report.get_by_text("Biểu mẫu có ô nhập mật khẩu.", exact=True)).to_be_visible()
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
        page.get_by_role("tab", name="Ghi âm").click()
        page.get_by_label("Chọn tệp ghi âm").set_input_files(fixture)
        page.get_by_role("button", name="Kiểm tra ngay").click()
        playwright.expect(page).to_have_url(WEB + "/website")
        playwright.expect(page.get_by_role("region", name="Kết quả phân tích")).to_be_visible(timeout=35000)
        assert page.evaluate("document.documentElement.scrollWidth === innerWidth")
        browser.close()


def test_audio_tab_checks_a_transcript_without_requiring_an_audio_file():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(WEB + "/website#kiem-tra-audio", wait_until="networkidle")
        panel = page.get_by_role("tabpanel", name="Ghi âm", exact=True)
        panel.get_by_text("Dán lời thoại hoặc thêm ngữ cảnh", exact=True).click()
        panel.get_by_label("Lời thoại hoặc nội dung đi kèm").fill("Hãy chuyển ngay vào tài khoản tạm giữ.")
        with page.expect_request("**/v1/analyze/stream") as call:
            panel.get_by_role("button", name="Kiểm tra ngay", exact=True).click()
        assert "audio_base64" not in call.value.post_data_json
        playwright.expect(panel.get_by_role("region", name="Kết quả phân tích")).to_be_visible(timeout=20000)
        browser.close()
