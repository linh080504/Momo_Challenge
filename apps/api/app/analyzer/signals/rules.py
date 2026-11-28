import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    pattern: str
    scenario: str | None
    tactic: str
    points: int
    finding: str
    context: str | None = None
    question: str | None = None
    accent_insensitive: bool = False


LOAN_CONTEXT = r"\b(?:khoản vay|yêu cầu vay|hồ sơ vay|đơn vay|vay vốn|vay tiền|giải ngân)\b"
JOB_CONTEXT = r"\b(?:tuyển (?:dụng|cộng tác viên)|ứng viên|làm việc tại nhà|việc làm online)\b"
ADVANCE_FEE = r"\b(?:nộp|đóng|chuyển|trả|thanh toán) (?:tiền )?(?:khoản )?phí "
SERVICE_FEE = r"\b(?:phi\s+(?:dich\s+vu|hang\s+thang)|cuoc\s+dich\s+vu)\b"
DEBIT_DEADLINE = r"\b(?:bi|se|tu\s+dong)\s+(?:bi\s+)?tru\b[^\r\n.!?]{0,25}\b\d{1,3}\s*(?:gio|phut)\b"
CANCEL_PROMPT = (
    r"\b(?:vui\s+long\s+)?(?:nhan|bam|truy\s+cap|click)\s+vao\b"
    r"(?=\s*\[?(?:link\b|duong\s+dan\b|nut\b|[^\s]{1,12}:\s*/{1,2})[\s\S]{0,85}\bde\s+huy\b)"
)

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
    Rule(LOAN_CONTEXT, None, "other", 0,
         "Tin nhắn đề cập một khoản vay. Thông báo trong tin nhắn cần được xác minh riêng.",
         question="Bạn có thực sự gửi hồ sơ và thấy cùng thông báo trên ứng dụng hoặc website chính thức của bên cho vay không?"),
    Rule(ADVANCE_FEE + r"(?:giải ngân|xác minh|bảo hiểm|trước khi (?:được )?(?:nhận tiền|giải ngân)|để (?:được )?giải ngân)\b",
         None, "other", 45,
         "Tin nhắn yêu cầu nộp phí để xử lý khoản vay. Hãy tạm dừng và đối chiếu trực tiếp với đơn vị cho vay.",
         context=LOAN_CONTEXT),
    Rule(JOB_CONTEXT, None, "other", 0,
         "Tin nhắn đề cập tuyển dụng. Vị trí và bên tuyển dụng vẫn cần xác minh.",
         question="Vị trí và thông tin liên hệ có xuất hiện trên kênh tuyển dụng chính thức của đơn vị không?"),
    Rule(r"\b(?:nạp tiền để (?:thực hiện nhiệm vụ|mua hàng|đặt đơn)|đóng thêm phí để rút tiền)\b",
         "G3.1", "greed", 45,
         "Tin tuyển dụng yêu cầu nạp tiền để làm nhiệm vụ hoặc đóng phí để rút tiền.",
         context=JOB_CONTEXT),
    Rule(ADVANCE_FEE + r"(?:tuyển dụng|nhận việc|giữ chỗ|xử lý hồ sơ)\b", "G3.1", "other", 40,
         "Tin tuyển dụng yêu cầu nộp phí liên quan đến việc ứng tuyển.", context=JOB_CONTEXT),
    Rule(DEBIT_DEADLINE, None, "urgency", 25,
         "Tin nhắn nói phí dịch vụ sẽ bị trừ trong thời gian ngắn, tạo áp lực phải phản ứng ngay.",
         context=SERVICE_FEE, accent_insensitive=True),
    Rule(CANCEL_PROMPT, "G5.1", "link", 40,
         "Tin nhắn thúc bấm vào đường dẫn hoặc nút để hủy khoản phí. Hãy tự mở ứng dụng chính thức để kiểm tra dịch vụ.",
         context=SERVICE_FEE + r"(?=[\s\S]{0,180}" + DEBIT_DEADLINE + r")",
         accent_insensitive=True),
)
BENIGN = re.compile(
    r"ăn cơm|họp lớp|không cung cấp mã|khong cung cap ma|không chuyển khoản|"
    r"đơn hàng .{0,80} đang được giao|có cần gia hạn không|(?:\+|\bnd:) *[\d.,]*vnd", re.I
)
NEGATION = re.compile(r"(?:không|đừng|chớ)\s+(?:(?:được|cần(?:\s+phải)?|phải|bao giờ)\s+)?$", re.I)


def match_rules(text):
    text = unicodedata.normalize("NFC", text)
    # Use one character per input character so excerpts still refer to the original wording.
    plain_text = "".join(
        "d" if char == "đ" else "D" if char == "Đ" else unicodedata.normalize("NFD", char)[0]
        for char in text
    )
    hits = []
    for rule in RULES:
        candidate = plain_text if rule.accent_insensitive else text
        if rule.context and not re.search(rule.context, candidate, re.I):
            continue
        for match in re.finditer(rule.pattern, candidate, re.I):
            if (rule.tactic == "credential_request" or rule.context) and NEGATION.search(text[max(0, match.start() - 24):match.start()]):
                continue
            hits.append((rule, text[match.start():match.end()]))
            break
    return sorted(hits, key=lambda item: item[0].points, reverse=True)
