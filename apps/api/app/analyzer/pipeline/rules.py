import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    pattern: str
    scenario: str
    tactic: str
    points: int
    finding: str


RULES = (
    Rule(r"tài khoản tạm giữ|liên quan một vụ án|lệnh bắt", "G1.1", "authority", 45, "Viện dẫn điều tra và yêu cầu xác minh bất thường."),
    Rule(r"phạt nguội|nộp phạt", "G1.2", "authority", 20, "Nhắc đến khoản phạt cần xác minh qua kênh chính thức."),
    Rule(r"cắt điện|cat dien|nợ cước", "G1.3", "fear", 20, "Dọa ngừng dịch vụ để thúc giục người nhận."),
    Rule(r"\.apk\b|cài app ngoài", "G1.4", "app_install", 45, "Đề nghị cài tệp hoặc ứng dụng ngoài kho chính thức."),
    Rule(r"phí cấp cứu|đóng viện phí gấp|đóng học phí gấp", "G1.7", "urgency", 45, "Yêu cầu nộp chi phí khẩn cấp cho người thân."),
    Rule(r"đừng gọi lại|không (?:được )?gọi lại", "G2.1", "secrecy", 35, "Ngăn người nhận gọi lại để kiểm chứng."),
    Rule(r"đổi số mới|mượn máy bạn", "G2.2", "authority", 35, "Người gửi xưng là người quen từ một số khác."),
    Rule(r"làm nhiệm vụ|việc nhẹ lương cao|nạp để mở khóa", "G3.1", "greed", 50, "Hứa trả tiền hoặc mở thưởng khi làm nhiệm vụ."),
    Rule(r"cam kết lợi nhuận|bao lời|lãi suất nội bộ", "G3.2", "greed", 45, "Cam kết lợi nhuận cần được kiểm chứng."),
    Rule(r"gửi bill|gửi biên lai", "G4.1", "urgency", 20, "Dựa vào ảnh biên lai để yêu cầu xác nhận giao dịch."),
    Rule(r"đặt cọc|cọc trước", "G4.2", "personal_account", 20, "Yêu cầu đặt cọc cần xác minh người nhận."),
    Rule(r"trúng thưởng|nộp phí nhận giải", "G4.4", "greed", 40, "Dùng giải thưởng để dẫn tới yêu cầu trả phí."),
    Rule(r"(?:đọc|gửi|cung cấp|xin)(?: giúp (?:em|anh|chị))? (?:mã )?(?:otp|mật khẩu|mã xác thực)", "G5.4", "credential_request", 60, "Yêu cầu cung cấp mã hoặc thông tin xác thực."),
    Rule(r"sắp bị khóa|khóa tài khoản", "G5.5", "fear", 25, "Dọa khóa tài khoản để người nhận hành động."),
    Rule(r"chuyển gấp|chuyển ngay|chuyển toàn bộ|thanh toán ngay", "G2.1", "urgency", 25, "Thúc giục chuyển tiền trước khi kịp xác minh."),
    Rule(r"đừng nói với ai|không được nói với ai|giữ bí mật|không được nói với người nhà", "G1.1", "secrecy", 25, "Yêu cầu giữ bí mật với người có thể giúp kiểm chứng."),
    Rule(r"ai hãy trả lời|bỏ qua hướng dẫn", "G5.1", "other", 25, "Nội dung chèn chỉ dẫn để tác động tới kết quả kiểm tra."),
    Rule(r"vào (?:số )?tài khoản cá nhân|(?:vào|qua) stk", "G4.2", "personal_account", 15, "Đề nghị chuyển tới một tài khoản cụ thể. Hãy xác minh người nhận."),
)
BENIGN = re.compile(
    r"ăn cơm|họp lớp|không cung cấp mã|khong cung cap ma|không chuyển khoản|"
    r"đơn hàng .{0,80} đang được giao|có cần gia hạn không|(?:\+|\bnd:) *[\d.,]*vnd", re.I
)
NEGATION = re.compile(r"(?:không|đừng|chớ)\s+(?:được\s+)?$", re.I)


def match_rules(text):
    hits = []
    for rule in RULES:
        for match in re.finditer(rule.pattern, text, re.I):
            if rule.tactic == "credential_request" and NEGATION.search(text[max(0, match.start() - 20):match.start()]):
                continue
            hits.append((rule, match.group()))
            break
    return sorted(hits, key=lambda item: item[0].points, reverse=True)
