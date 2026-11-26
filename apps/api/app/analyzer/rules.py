"""Text rules for the hybrid score (rule part) — RULES_VERSION "rules_v1".

Points follow .claude/skills/scam-analyzer/risk-scoring.md where a row exists. Rows marked NEW are
not in risk-scoring.md yet: proposed to PM, to be confirmed or re-weighted from eval results
(risk-scoring.md: "Điều chỉnh trọng số chỉ dựa trên kết quả eval").

| Signal id            | Points | Source                                                        |
|----------------------|--------|---------------------------------------------------------------|
| credential_request   | +50    | risk-scoring: Yêu cầu OTP, mật khẩu, mã xác thực              |
| app_install          | +45    | risk-scoring: Yêu cầu cài app ngoài kho (link .apk)           |
| gov_personal_account | +40    | risk-scoring: Tự xưng cơ quan + chuyển tiền vào TK cá nhân    |
| urgency/fear/secrecy | +10 ea | risk-scoring: từ khóa gấp/dọa/giữ bí mật (mỗi loại)            |
| prompt_injection     | +35    | NEW — quy tắc vàng: câu ra lệnh cho AI là dấu hiệu lừa đảo     |
| scenario:<id>        | +35    | NEW — mẫu đặc trưng của 1 trong 25 mã taxonomy (tính 1 lần)    |
| money_request        | +10    | NEW — đòi chuyển/nộp/nạp tiền                                  |
| personal_account     | +10    | NEW — nhận tiền qua TK cá nhân/người khác (không kèm cơ quan)  |
(domain_check, danh sách đen, danh sách trắng: xem evidence/ và scoring.py.)

Pure functions, no I/O, no logging of input text.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .text import Doc, Pattern, compile_pattern, quote_for

RULES_VERSION = "rules_v1"

P_CREDENTIAL = 50
P_APP_INSTALL = 45
P_GOV_PERSONAL = 40
P_TACTIC_KEYWORD = 10
P_INJECTION = 35
P_SCENARIO = 35
P_MONEY = 10
P_PERSONAL_ACCOUNT = 10


@dataclass
class Signal:
    id: str
    points: int
    reason: str
    tactic: str = "other"
    quote: str | None = None
    scenario_id: str | None = None


@dataclass
class TextRuleResult:
    signals: list[Signal] = field(default_factory=list)
    scenario_id: str | None = None   # best strong match
    topic_id: str | None = None      # weak topical hint (0 points)

    @property
    def score(self) -> int:
        return sum(s.points for s in self.signals)


def _c(*patterns: str) -> list[Pattern]:
    return [compile_pattern(p) for p in patterns]


# Reusable fragments (lowercase accented; folded automatically).
YOU = r"(anh|chị|ông|bà|bạn|quý khách|quý vị|em|cô|chú|cháu|con)"
AUTHORITY = (r"(công an|bộ công an|cảnh sát|csgt|viện kiểm sát|tòa án|cơ quan điều tra|điều tra viên|"
             r"cục thuế|chi cục thuế|cơ quan thuế|bhxh|bảo hiểm xã hội|ngân hàng nhà nước|điện lực|evn|"
             r"ubnd|ủy ban nhân dân|thanh tra|hải quan|bộ tài chính|bộ y tế|an ninh mạng)")
BANKS = (r"(vietcombank|vcb|bidv|agribank|techcombank|vietinbank|mb ?bank|tpbank|vpbank|acb|sacombank|"
         r"hdbank|shb|ocb|vib|seabank|msb|eximbank|ngân hàng)")
LINKISH = r"(https?://|www\.|bấm vào|nhấn vào|truy cập|đường link|đường dẫn|tại link|theo link|vào link|link)"
STORE = _c(r"(app store|appstore|ch play|chplay|google play|play store|kho ứng dụng)")


@dataclass(frozen=True)
class Scenario:
    id: str
    reason: str
    tactic: str
    strong: list[Pattern]
    topic: list[Pattern] = field(default_factory=list)
    points: int = P_SCENARIO
    store_exempt: bool = False  # skip strong match if an official app store is mentioned nearby


# Priority order = more specific first. 25 working codes from taxonomy.md (G5.3/G5.4 come from
# app_install / credential_request signals below; G5.3 also has remote-control patterns here).
SCENARIOS: list[Scenario] = [
    Scenario("G1.7", "Tự xưng bệnh viện hoặc nhà trường, báo người thân cấp cứu hoặc đòi đóng phí gấp.", "urgency",
             _c(r"(bệnh viện|khoa cấp cứu|phòng cấp cứu|bác sĩ|nhà trường|trường (học|mầm non|tiểu học|thcs|thpt)|"
                r"giáo viên|cô giáo|thầy giáo|phòng đào tạo|ban giám hiệu|chủ nhiệm).{0,150}"
                r"(cấp cứu|tai nạn|nguy kịch|chấn thương|phẫu thuật|mổ gấp|hôn mê|bị ngã|đánh nhau).{0,150}"
                r"(chuyển|tạm ứng|đóng|nộp|viện phí|chi phí|tiền)",
                r"(bệnh viện|nhà trường|giáo viên|cô giáo|thầy giáo|phòng đào tạo).{0,120}"
                r"(đóng|nộp|chuyển)( gấp| ngay)? (phí|tiền|học phí|quỹ|bảo hiểm).{0,80}(gấp|ngay|kẻo|nếu không|không thì)"),
             _c(r"(bệnh viện|cấp cứu|nhà trường|học phí|viện phí|giáo viên chủ nhiệm)")),
    Scenario("G1.6", "Kịch bản \"bắt cóc online\": dọa người thân bị giữ, đòi tiền và cấm liên lạc.", "fear",
             _c(r"tiền chuộc",
                r"(bắt cóc|giam giữ|tạm giữ|bị bắt).{0,100}(con|cháu|em) .{0,100}(chuyển|tiền|bảo lãnh)",
                r"(con|cháu) (của )?(anh|chị|ông|bà|bạn|cô|chú) .{0,80}(bị bắt|bị giữ|bị tạm giữ|đang bị điều tra|liên quan)",
                r"(thuê|ở một mình|cách ly).{0,40}(khách sạn|nhà nghỉ).{0,100}(không được|cấm) (liên lạc|nói|kể)")),
    Scenario("G1.1", "Tự xưng công an, viện kiểm sát, tòa án và nói bạn liên quan vụ án.", "authority",
             _c(YOU + r" .{0,60}(liên quan|dính líu|có tên trong|bị điều tra|bị khởi tố|bị truy nã|có lệnh bắt|đứng tên)"
                r".{0,80}(vụ án|đường dây|rửa tiền|ma túy|lừa đảo|buôn lậu|hồ sơ)",
                r"lệnh (bắt|tạm giam|truy nã) .{0,20}(đối với|của) " + YOU,
                r"(giấy|lệnh) triệu tập|giấy mời làm việc"),
             _c(r"(công an|viện kiểm sát|tòa án|cơ quan điều tra|điều tra viên|cán bộ điều tra)")),
    Scenario("G1.2", "Báo phạt nguội nhưng bắt nộp tiền hoặc bấm link.", "authority",
             _c(r"(phạt nguội|vi phạm giao thông|biên bản vi phạm|quá tốc độ|vượt đèn đỏ).{0,150}"
                r"(chuyển khoản|nộp phạt (qua|vào|tại|theo)|đóng phạt (qua|vào|tại)|tải (app|ứng dụng)|" + LINKISH + ")"),
             _c(r"(phạt nguội|vi phạm giao thông|biên bản vi phạm|cảnh sát giao thông|csgt)")),
    Scenario("G1.3", "Dọa cắt điện, khóa sim vì nợ cước để ép thanh toán.", "fear",
             _c(r"(cắt điện|ngừng cấp điện|tạm ngừng cung cấp điện|cắt sim|khóa sim|khóa (2|hai) chiều|thu hồi (số|sim)|"
                r"ngắt (dịch vụ|thuê bao)).{0,150}(thanh toán|chuyển khoản|chuyển tiền|nộp tiền|đóng tiền|" + LINKISH + ")",
                r"(nợ cước|nợ tiền điện|chưa thanh toán (tiền điện|cước)).{0,120}(cắt|khóa|ngừng|thu hồi)"),
             _c(r"(nợ cước|cước viễn thông|tiền điện|điện lực|nhà mạng|thuê bao)")),
    Scenario("G1.4", "Tự xưng BHXH, dịch vụ công, thuế và bắt cài app hoặc bấm link.", "authority",
             _c(r"(bhxh|bảo hiểm xã hội|dịch vụ công|vneid|định danh|căn cước|cccd|sinh trắc|thuế).{0,150}"
                r"(cài (đặt )?(app|ứng dụng)|tải (app|ứng dụng|về)|\.apk|kết bạn zalo|" + LINKISH + ")"),
             _c(r"(bhxh|bảo hiểm xã hội|dịch vụ công|vneid|định danh điện tử|sinh trắc học|hoàn thuế|quyết toán thuế)"),
             store_exempt=True),
    Scenario("G1.5", "Giả tin nhắn ngân hàng báo khóa tài khoản và gửi link.", "fear",
             _c(r"(" + BANKS[1:-1] + r"|tài khoản (của )?(quý khách|bạn)).{0,150}"
                r"(bị (tạm )?khóa|sẽ bị khóa|tạm ngưng|bị đóng băng|hết hạn|nâng cấp|cập nhật|xác thực|xác minh|"
                r"kích hoạt lại|đăng nhập).{0,100}" + LINKISH),
             _c(BANKS)),
    Scenario("G2.3", "Giả sếp, lãnh đạo nhắn chuyển tiền gấp, không cho gọi lại.", "authority",
             _c(r"(sếp|giám đốc|tổng giám đốc|trưởng phòng|lãnh đạo|chủ tịch|phó giám đốc|kế toán trưởng).{0,150}"
                r"(chuyển (khoản|tiền|gấp|ngay)|thanh toán (gấp|ngay|cho đối tác)|ứng (tiền|trước)|mua (thẻ|card)).{0,150}"
                r"(gấp|ngay|đang họp|bận họp|không gọi được|không nghe máy|bí mật|đừng (nói|báo))"),
             _c(r"(video call|gọi video|cuộc gọi video|đang họp|đang bận họp)")),
    Scenario("G2.2", "Người quen \"đổi số mới\" hoặc mất nick rồi hỏi mượn tiền.", "personal_account",
             _c(r"(đổi số|số mới|số cũ (bị )?(hỏng|mất)|mất điện thoại|điện thoại (bị )?(hỏng|mất|rơi)|zalo mới|nick mới|"
                r"mất nick|bị hack (nick|facebook|zalo)|sim (bị )?(hỏng|khóa)).{0,200}"
                r"(mượn|vay|ứng|chuyển (giúp|hộ|cho|tạm|gấp)|gửi (giúp|hộ|tạm)|cần tiền|cần gấp)",
                r"(chuyển|gửi) (giúp|hộ|vào|qua) (tài khoản|stk) (của )?(bạn|người quen|em họ|chị|anh|đứa em|đồng nghiệp|"
                r"bạn mình|bạn em|người nhà)"),
             _c(r"(mượn tiền|vay tiền|cho (mình|tớ|em) mượn)")),
    Scenario("G2.1", "Báo người thân gặp nạn và cần tiền gấp.", "urgency",
             _c(r"(bố|mẹ|ba|má|anh|chị|em|con|cháu|chồng|vợ|ông|bà|người nhà).{0,60}"
                r"(bị tai nạn|gặp tai nạn|gặp nạn|cấp cứu|bị bắt|bị công an giữ|nhập viện|đang nằm viện|bị đánh|gây tai nạn)"
                r".{0,150}(chuyển (gấp|ngay|tiền|khoản|giúp|cho)|cần (gấp )?tiền|gửi (gấp )?tiền|tạm ứng|lo tiền|"
                r"đóng viện phí|bồi thường)",
                r"(đang cần tiền gấp|cần tiền gấp|chuyển gấp cho (em|anh|chị|mình|con|mẹ|bố))"),
             _c(r"(tai nạn|gặp nạn|cấp cứu|nhập viện)")),
    Scenario("G2.4", "Xin bạn đọc to một câu, có thể để thu mẫu giọng.", "other",
             _c(r"(đọc|nói|lặp lại) (to |lại |theo )?(câu|đoạn|dãy số|các số|vài câu).{0,80}(xác minh|ghi âm|giọng|khảo sát|xác thực)"),
             _c(r"(thu âm|mẫu giọng|xác minh giọng nói)")),
    Scenario("G3.4", "Làm quen tình cảm qua mạng rồi rủ đầu tư hoặc nhận quà phải nộp phí.", "greed",
             _c(r"(anh yêu|em yêu|người yêu|vợ yêu|chồng yêu|honey|baby|kết hôn|làm quen|quen (nhau )?qua (mạng|facebook|zalo|app)|"
                r"về việt nam|ở nước ngoài|quân nhân|kỹ sư dầu khí).{0,300}"
                r"(đầu tư|sàn|nạp tiền|lợi nhuận|gửi quà|hải quan|phí (vận chuyển|thông quan|nhận quà)|kiện hàng)")),
    Scenario("G3.3", "Mời gửi tiết kiệm lãi suất \"ưu đãi nội bộ\" cao bất thường.", "greed",
             _c(r"(lãi suất|gói tiết kiệm|tiết kiệm|gửi tiền).{0,60}(ưu đãi nội bộ|nội bộ|dành riêng cho (khách )?vip|đặc biệt cao)",
                r"ưu đãi nội bộ",
                r"(tiết kiệm|gửi tiền|gửi góp).{0,40}lãi suất (lên (tới|đến) )?(1[0-9]|[2-9][0-9])([.,][0-9]+)? ?%")),
    Scenario("G3.2", "Mời đầu tư, cam kết lợi nhuận cao, không rủi ro.", "greed",
             _c(r"(cam kết|đảm bảo|chắc chắn|bảo đảm) (lợi nhuận|lãi|sinh lời|có lãi|lời)",
                r"lợi nhuận (lên (tới|đến) )?[0-9]+ ?%.{0,20}(ngày|tuần|tháng)",
                r"lãi [0-9]+([.,][0-9]+)? ?% ?(/|mỗi|một|1|trên)? ?(ngày|tuần)",
                r"(x2|x3|x5|x10|nhân đôi|gấp đôi|gấp [0-9]+ lần) (tài khoản|vốn|số tiền|tiền)",
                r"không (rủi ro|lỗ|thua lỗ)",
                r"(chuyên gia|mentor|thầy).{0,40}(kéo|tín hiệu|phím hàng|soi kèo)",
                r"(sàn|nền tảng|app) (đầu tư|giao dịch|forex|coin|tiền ảo|chứng khoán).{0,100}(nạp|lợi nhuận|rút tiền|mở khóa|phí rút)"),
             _c(r"(đầu tư|chứng khoán|tiền ảo|tiền số|tiền điện tử|crypto|bitcoin|usdt|forex|ngoại hối|sàn giao dịch)")),
    Scenario("G3.1", "Mời \"việc nhẹ lương cao\", làm nhiệm vụ, phải nạp tiền trước.", "greed",
             _c(r"việc nhẹ lương cao|làm nhiệm vụ",
                r"nhiệm vụ (thả tim|like|đánh giá|đơn hàng|tăng tương tác|xem video|follow)",
                r"(cộng tác viên|ctv).{0,100}(hoa hồng|nhiệm vụ|đơn ảo|nạp|ứng trước)",
                r"(nạp|ứng|thanh toán) (tiền )?(trước|đơn).{0,100}(hoa hồng|hoàn (lại|vốn|tiền)|nhận lại|rút)",
                r"hoa hồng [0-9]+ ?%",
                r"(thu nhập|lương|kiếm|nhận) (từ )?[0-9]+([.,][0-9]+)? ?(k|tr|triệu|nghìn|ngàn|đ)?"
                r"( ?/ ?| mỗi | một | 1 )(ngày|giờ|buổi|ca)\b",
                r"không cần kinh nghiệm.{0,80}(thu nhập|lương|hoa hồng)"),
             _c(r"(tuyển dụng|tuyển (gấp )?(ctv|cộng tác viên|nhân viên)|việc làm (online|tại nhà)|làm thêm)")),
    Scenario("G4.1", "Báo đã chuyển tiền, đưa ảnh bill hoặc nói chuyển nhầm để đòi trả lại.", "other",
             _c(r"(chuyển|ck) (nhầm|thừa|dư|lộn).{0,120}(trả lại|hoàn lại|chuyển lại|gửi lại|hoàn trả)",
                r"(bill|biên lai|ảnh chuyển khoản).{0,80}(tiền (chưa|sẽ) về|chờ (ngân hàng )?xử lý|bị treo|treo)"),
             _c(r"(bill|biên lai|ủy nhiệm chi|ảnh chuyển khoản)")),
    Scenario("G4.5", "Hứa hoàn tiền, bồi thường đơn hàng nhưng bắt kết bạn Zalo, bấm link hoặc đưa thông tin.", "greed",
             _c(r"(hoàn tiền|hoàn trả|bồi thường|đền bù|hoàn phí).{0,150}(kết bạn zalo|liên hệ zalo|qua zalo|nhắn zalo|"
                r"tải (app|ứng dụng)|cài (app|ứng dụng)|cung cấp (stk|số tài khoản|số thẻ|otp|mã)|nhân viên (cskh|chăm sóc khách hàng)|"
                + LINKISH + ")"),
             _c(r"(hoàn tiền|bồi thường|đền bù)")),
    Scenario("G4.4", "Báo trúng thưởng, nhận quà nhưng phải nộp phí hoặc bấm link.", "greed",
             _c(r"(trúng thưởng|trúng giải|quà tặng|quà tri ân|tri ân khách hàng|may mắn (được|trúng)|được chọn|nhận quà|"
                r"phần thưởng|giải (nhất|nhì|ba|đặc biệt)|chúc mừng (bạn|quý khách|anh|chị)).{0,150}"
                r"(phí|nộp|chuyển khoản|chuyển tiền|thuế (thu nhập|tncn)|đóng|làm thủ tục|liên hệ zalo|kết bạn zalo|"
                + LINKISH + ")"),
             _c(r"(trúng thưởng|quà tặng|tri ân|chúc mừng (bạn|quý khách))")),
    Scenario("G4.3", "Giả shipper, bưu điện đòi chuyển khoản phí hoặc bấm link.", "other",
             _c(r"(shipper|giao hàng|bưu điện|bưu phẩm|bưu kiện|kiện hàng|ghtk|ghn|viettel ?post|j&t|vnpost).{0,150}"
                r"(chuyển khoản|ck|chuyển tiền|thanh toán (qua|tại|theo) (link|đường dẫn)|https?://|bấm vào|truy cập).{0,80}"
                r"(phí|cước|tiền (ship|hàng|cod)|lưu kho|hải quan|địa chỉ)",
                r"phí (ship|vận chuyển|lưu kho|phát lại|hải quan|thông quan).{0,80}(chuyển khoản|ck|link|https?://|bấm vào)"),
             _c(r"(shipper|giao hàng|đơn hàng|kiện hàng|bưu phẩm|bưu điện)")),
    Scenario("G4.2", "Đòi đặt cọc gấp để giữ phòng, vé, hàng.", "urgency",
             _c(r"(đặt cọc|cọc|giữ (chỗ|phòng|vé|hàng|slot)).{0,120}(gấp|ngay|kẻo|hết (phòng|vé|hàng|chỗ|slot)|chỉ còn [0-9]+|"
                r"nhiều người (hỏi|đặt|lấy)|trong (hôm nay|[0-9]+ ?(phút|giờ|h)))",
                r"(chuyển|ck) (cọc|tiền cọc).{0,80}(mới|thì|để) (giữ|gửi|giao|xác nhận|lên đơn)",
                r"(vé|phòng|homestay|tour).{0,60}(giá (rẻ|sốc|hời)|thanh lý|pass lại).{0,100}(cọc|chuyển khoản|ck)"),
             _c(r"(đặt cọc|tiền cọc|giữ (chỗ|phòng|vé))")),
    Scenario("G5.5", "Dọa khóa tài khoản mạng xã hội và gửi link \"kháng nghị\".", "fear",
             _c(r"(facebook|fb|zalo|instagram|tiktok|fanpage|meta|tài khoản (mạng xã hội|facebook|zalo|tiktok)).{0,150}"
                r"(bị (tạm )?khóa|sẽ bị (khóa|xóa|vô hiệu hóa|gỡ)|vi phạm (tiêu chuẩn|bản quyền|chính sách|điều khoản)|vô hiệu hóa)"
                r".{0,150}(kháng nghị|khiếu nại|xác minh|xác nhận|" + LINKISH + ")")),
    Scenario("G5.2", "Bảo quét mã QR để nhận tiền, hoàn tiền hoặc xác thực.", "link",
             _c(r"(quét|scan) (mã )?qr.{0,100}(nhận (tiền|quà|thưởng|hoàn|lại)|hoàn tiền|xác thực|xác minh|đăng nhập|kích hoạt|"
                r"mở khóa|cập nhật)",
                r"mã qr (này |dưới |sau )?(để )?(nhận|hoàn|xác)")),
    Scenario("G5.3", "Bảo cài phần mềm điều khiển máy từ xa hoặc chia sẻ màn hình.", "app_install",
             _c(r"(teamviewer|anydesk|ultraviewer|airdroid|rustdesk|chia sẻ màn hình|điều khiển (từ xa|máy))"),
             points=P_APP_INSTALL),
    Scenario("G5.1", "Bảo đăng nhập hoặc xác minh tài khoản qua một đường link.", "link",
             _c(r"(đăng nhập|xác thực|xác minh|cập nhật thông tin|kích hoạt|khôi phục).{0,80}(tại|qua|theo|vào|ở) "
                r"(link|đường dẫn|đường link|trang|website)"),
             points=20),
]

# ---- tactic signals -------------------------------------------------------------------------

CRED = r"(mã otp|otp|smart ?otp|mã (xác thực|xác nhận|bảo mật|kích hoạt|pin|giao dịch)|mật khẩu|password|mật mã|mã cvv|cvv|số thẻ)"
CRED_VERB_BEFORE = _c(r"(cung cấp|gửi|đọc|báo|cho (em|mình|tôi|anh|chị|bên (em|mình)) (xin|biết)?|xin|nhắn( lại)?|chụp|điền|"
                      r"xác nhận|chia sẻ|chuyển tiếp|soạn|hỏi|yêu cầu)( [^ .!?\n]+){0,4}? " + CRED)
CRED_VERB_AFTER = _c(CRED + r".{0,60}(đọc lại|gửi lại|báo lại|nhắn lại|đọc (giúp|cho)|gửi (giúp|cho) (em|mình|tôi)|"
                            r"cho (em|mình|tôi|bên em) (xin|biết))")
CRED_INTO_LINK = _c(r"(nhập|điền) (mã )?" + CRED + r".{0,40}(vào|tại|trên|qua) (link|đường (dẫn|link)|trang|web|website|form|biểu mẫu|đây)")
# "không / đừng / không bao giờ ... cung cấp OTP" = legitimate warning, not a request.
NEGATION_TAIL = compile_pattern(r"(không|đừng|chớ|tuyệt đối không|không bao giờ|chưa bao giờ|không được|không nên|nghiêm cấm|ko|hok|hông)"
                                r"( [^ .!?\n]+){0,5} ?$")
STATEMENT_TAIL = compile_pattern(r"(đã|vừa|được|sẽ) $")
PAST_TAIL = compile_pattern(r"(đã|vừa|mới|được|bị) ([^ ]+ )?$")

APK = _c(r"\.apk\b")
APP_INSTALL = _c(r"(cài|tải)( đặt| về| xuống)? (app|ứng dụng|phần mềm|apk)")
APP_OFFSTORE_HINT = _c(r"(theo|qua|tại|vào) (link|đường (dẫn|link))|(không|chưa) có trên (ch play|app store|kho)|https?://|www\.")

GOV_TRANSFER = _c(r"(chuyển|nộp|đóng|gửi)( tiền| khoản| phạt| phí)?.{0,40}(vào|qua|tới|đến|cho) (tài khoản|stk|số tài khoản|tk)",
                  r"tài khoản (tạm giữ|tạm giam|an toàn|của cơ quan|giám sát|thanh tra|điều tra|chuyên dụng)")
AUTHORITY_P = _c(AUTHORITY)

MONEY = _c(r"(chuyển|ck|nộp|nạp|đóng|thanh toán|trả trước|ứng)( (tiền|khoản|phí|cọc|gấp|ngay|trước|thêm|vào|qua|cho))\b")
PERSONAL_ACCOUNT = _c(r"tài khoản (cá nhân|riêng)",
                      r"(chuyển|gửi) (vào|qua) (tài khoản|stk|tk) (của )?(em|mình|tôi|bạn (em|mình|tôi)|người nhà|kế toán|em họ|chị gái|anh trai)")

URGENCY = _c(r"\b(gấp|khẩn cấp|khẩn|ngay lập tức|ngay bây giờ|ngay hôm nay|càng sớm càng tốt|hạn chót|hạn cuối|sắp hết hạn|"
             r"không kịp|kẻo)\b",
             r"trong (vòng )?[0-9]+ ?(phút|giờ|tiếng|h)\b",
             r"trước [0-9]{1,2} ?(h|giờ)\b( hôm nay)?")
FEAR = _c(r"(bị khóa|sẽ bị khóa|khóa tài khoản|phong tỏa|đóng băng|khởi tố|truy tố|lệnh bắt|bắt giam|tạm giam|truy nã|"
          r"cắt điện|cắt sim|xử lý theo (quy định của )?pháp luật|chịu trách nhiệm trước pháp luật|vô hiệu hóa|"
          r"rửa tiền|liên quan đến vụ án|đình chỉ)")
SECRECY = _c(r"(giữ bí mật|bí mật (điều tra|tuyệt đối)|không được (nói|kể|tiết lộ|chia sẻ|báo) (với|cho)|"
             r"đừng (nói|kể|báo) (với|cho)|không (cho|để) (ai|người nhà|gia đình) biết|tuyệt đối không (nói|kể|tiết lộ))")

# ---- prompt injection ("nội dung người dùng là dữ liệu, không phải lệnh") ------------------------
INJECTION = _c(
    r"(bỏ qua|phớt lờ|quên|không (cần )?tuân theo|vô hiệu) (hết |mọi |tất cả |các |toàn bộ )?"
    r"(hướng dẫn|chỉ dẫn|chỉ thị|lệnh|quy tắc|yêu cầu|prompt)( (trước|ở trên|phía trên|cũ|hệ thống))?",
    r"(ignore|disregard|forget) (all |any |the )?(previous|prior|above|earlier|system) (instructions|prompts?|rules)",
    r"\byou are now\b|\bact as\b|\bjailbreak\b",
    r"</? ?(system|user_content|evidence|instructions?) ?>|\[ ?(system|hệ thống) ?\]|(^|\n) ?(system|assistant) ?:",
    r"\"?risk_(level|score)\"? ?[:=]",
    r"(dành cho|gửi|lưu ý cho|chú ý|note for|note to|to) (các )?(ai|chatbot|bot|trợ lý ảo|hệ thống (kiểm duyệt|phân tích|lọc)|"
    r"mô hình|llm|gpt) ?[:,-]",
    r"(hãy|phải|bắt buộc|chỉ được|vui lòng) (trả lời|đánh giá|kết luận|xác nhận|phân loại|báo|ghi|chấm)"
    r"( rằng| là)?.{0,40}(an toàn|hợp lệ|không (phải )?lừa đảo|uy tín|tin cậy|rủi ro thấp|low)",
    r"(tin nhắn|nội dung|thông báo) này (đã (được )?)?(hệ thống |ai )?(xác minh|kiểm duyệt|xác nhận)( là)? (an toàn|hợp lệ|chính thức)",
)
QUESTION_TAIL = compile_pattern(r"^ ?(không|ko|hông|chưa|hay không|hay ko|hả|ạ ?\?|\?)")


def _first(doc: Doc, patterns: list[Pattern]):
    for p in patterns:
        for s, e, m in doc.finditer(p):
            return s, e, m
    return None


def _all(doc: Doc, patterns: list[Pattern]):
    for p in patterns:
        yield from doc.finditer(p)


def _tail_matches(p: Pattern, doc: Doc, view_text: str) -> bool:
    rx = p.accented if doc.accented_mode else p.folded
    return rx.search(view_text) is not None


def _q(doc: Doc, s: int, e: int) -> str:
    return quote_for(doc.text, s, e)


def _credential_request(doc: Doc):
    for s, e, m in _all(doc, CRED_INTO_LINK):
        return s, e
    for s, e, m in _all(doc, CRED_VERB_BEFORE + CRED_VERB_AFTER):
        before = m.string[max(0, m.start() - 60):m.start()]
        if _tail_matches(NEGATION_TAIL, doc, before) or _tail_matches(STATEMENT_TAIL, doc, before[-8:]):
            continue
        return s, e
    return None


def _injection(doc: Doc):
    for s, e, m in _all(doc, INJECTION):
        after = m.string[m.end():m.end() + 14]
        if _tail_matches(QUESTION_TAIL, doc, after):
            continue  # "đánh giá giúp tin này có an toàn không?" is the user's own question
        return s, e
    return None


def _near_store(doc: Doc, s: int, e: int) -> bool:
    window = Doc(doc.text[max(0, s - 80):e + 80])
    return _first(window, STORE) is not None


def evaluate_text(text: str, has_offstore_url: bool = False) -> TextRuleResult:
    """Score the text-only rules. `has_offstore_url`: the input contains a URL that is not an official
    domain / app store (computed by the evidence step)."""
    doc = Doc(text)
    res = TextRuleResult()
    if not doc.text.strip():
        return res
    add = res.signals.append

    hit = _credential_request(doc)
    if hit:
        add(Signal("credential_request", P_CREDENTIAL, "Đòi bạn đưa mã OTP, mật khẩu hoặc mã xác thực. "
                   "Ngân hàng và cơ quan nhà nước không bao giờ xin những mã này.",
                   "credential_request", _q(doc, *hit), "G5.4"))

    hit = _first(doc, APK)
    if not hit:
        inst = _first(doc, APP_INSTALL)
        if inst and not _near_store(doc, inst[0], inst[1]) and (has_offstore_url or _first(doc, APP_OFFSTORE_HINT)):
            hit = inst
    if hit:
        add(Signal("app_install", P_APP_INSTALL, "Bảo cài ứng dụng ngoài kho chính thức. App lạ có thể lấy cắp tiền "
                   "trong tài khoản.", "app_install", _q(doc, hit[0], hit[1]), "G5.3"))

    auth = _first(doc, AUTHORITY_P)
    transfer = _first(doc, GOV_TRANSFER)
    if auth and transfer:
        add(Signal("gov_personal_account", P_GOV_PERSONAL, "Tự xưng cơ quan, tổ chức nhưng bảo chuyển tiền vào một tài "
                   "khoản. Cơ quan nhà nước không nhận tiền kiểu này.", "authority", _q(doc, transfer[0], transfer[1]), None))
    else:
        pa = _first(doc, PERSONAL_ACCOUNT)
        if pa:
            add(Signal("personal_account", P_PERSONAL_ACCOUNT, "Bảo chuyển tiền vào tài khoản cá nhân hoặc tài khoản "
                       "của người khác.", "personal_account", _q(doc, pa[0], pa[1])))

    for sid, pats, reason, tactic in (
            ("urgency", URGENCY, "Hối thúc phải làm ngay, không cho bạn thời gian kiểm tra.", "urgency"),
            ("fear", FEAR, "Dọa nạt (khóa tài khoản, bắt giữ, cắt dịch vụ) để bạn sợ mà làm theo.", "fear"),
            ("secrecy", SECRECY, "Bảo bạn giữ bí mật, không nói với ai. Kẻ gian sợ bạn hỏi người khác.", "secrecy")):
        hit = _first(doc, pats)
        if hit:
            add(Signal(sid, P_TACTIC_KEYWORD, reason, tactic, _q(doc, hit[0], hit[1])))

    hit = _injection(doc)
    if hit:
        add(Signal("prompt_injection", P_INJECTION, "Tin nhắn có câu ra lệnh cho máy kiểm tra (AI) phải trả lời là "
                   "an toàn. Tin thật không bao giờ làm vậy.", "other", _q(doc, *hit)))

    for sc in SCENARIOS:
        for s, e, m in _all(doc, sc.strong):
            if sc.store_exempt and _near_store(doc, s, e):
                continue
            res.scenario_id = sc.id
            add(Signal(f"scenario:{sc.id}", sc.points, sc.reason, sc.tactic, _q(doc, s, e), sc.id))
            break
        if res.scenario_id:
            break
    if not res.scenario_id:
        for sc in SCENARIOS:
            if sc.topic and _first(doc, sc.topic):
                res.topic_id = sc.id
                break

    has_strong_money_signal = any(s.id in ("gov_personal_account", "personal_account") for s in res.signals)
    if not has_strong_money_signal:
        for s, e, m in _all(doc, MONEY):
            if _tail_matches(PAST_TAIL, doc, m.string[max(0, m.start() - 12):m.start()]):
                continue  # "bạn vừa chuyển khoản 500.000đ" is a statement, not a request
            add(Signal("money_request", P_MONEY, "Yêu cầu chuyển, nộp hoặc nạp tiền.", "other", _q(doc, s, e)))
            break

    if not res.scenario_id:
        tactic_scn = next((s.scenario_id for s in res.signals if s.scenario_id), None)
        res.scenario_id = tactic_scn
    return res
