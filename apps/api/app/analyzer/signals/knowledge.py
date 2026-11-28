import re

VERSION = "2026-11-27.1"
BANK = "https://www.vietcombank.com.vn/vi-VN/KHCN/Danh-sach-nguyen-tac-GDAT/"
CARDS = {
    "G1": ("Xác minh yêu cầu qua số công khai của cơ quan hoặc đơn vị được nhắc đến.", BANK),
    "G2": ("Liên lạc với người quen qua số cũ hoặc một kênh liên lạc đã biết.",
           "https://consumer.ftc.gov/consumer-alerts/2025/03/what-are-signs-scam"),
    "G3": ("Kiểm tra trang tuyển dụng chính thức. Dừng lại nếu được yêu cầu phí, tiền cọc hoặc mã xác thực.",
           "https://vietcombank.com.vn/vi-VN/Trang-thong-tin-dien-tu/Articles/2025/08/20/20250819_NMH_Canh-bao-lua-dao-VCBxVietlott"),
    "G4": ("Kiểm tra người nhận và lịch sử giao dịch trực tiếp trong ứng dụng ngân hàng.", BANK),
    "G5": ("Tự mở ứng dụng chính thức. Giữ riêng mã xác thực và mật khẩu.",
           "https://www.momo.vn/hoi-dap/nhan-biet-dau-hieu-lua-dao-nhu-the-nao"),
    "black-friday": ("Mở cửa hàng từ ứng dụng hoặc địa chỉ bạn đã biết và kiểm tra người bán trước khi thanh toán ưu đãi.",
                     "https://consumer.ftc.gov/consumer-alerts/2025/11/how-avoid-online-shopping-scam-holiday-season"),
}
SEASONAL = re.compile(r"\bblack[ -]+friday\b", re.I)


def retrieve_guidance(matches, url_suspicious, text=""):
    groups = dict.fromkeys(rule.scenario.split(".")[0] for rule, _ in matches if rule.scenario)
    if url_suspicious:
        groups.setdefault("G5", None)
    keys = ["black-friday"] if SEASONAL.search(text) else []
    keys.extend(groups)
    return [{"id": f"paypause-taxonomy-{key}", "text": CARDS[key][0], "source_url": CARDS[key][1],
             "version": VERSION} for key in keys[:3]]
