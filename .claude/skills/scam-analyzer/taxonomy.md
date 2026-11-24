# Taxonomy thủ đoạn lừa đảo (bản làm việc)

Khung 5 nhóm lấy từ cảnh báo "25 kịch bản lừa đảo trên không gian mạng năm 2026" của Công an TP Hà Nội (09/2026).
Các báo đăng lại chỉ nêu 5 nhóm, không liệt kê đủ 25 kịch bản; các kịch bản con dưới đây do đội tổng hợp từ cảnh báo và báo chí.
**Việc của ngày 1:** tìm thông báo gốc, đối chiếu và bổ sung đủ 25 mã kịch bản.

| Nhóm | Tên | Kịch bản con (mã) | Dấu hiệu chính | Câu hỏi kiểm chứng gợi ý |
|---|---|---|---|---|
| G1 | Mạo danh cơ quan, tổ chức | G1.1 công an/viện kiểm sát/tòa án báo liên quan vụ án; G1.2 nộp phạt nguội; G1.3 nợ cước viễn thông, cắt điện; G1.4 BHXH/dịch vụ công yêu cầu cài app; G1.5 brandname ngân hàng giả; G1.6 "bắt cóc online" học sinh, sinh viên | Cơ quan yêu cầu chuyển tiền vào tài khoản cá nhân; dọa; đòi giữ bí mật; gửi link/APK | "Cơ quan nhà nước có bao giờ làm việc qua Zalo và nhận tiền vào tài khoản cá nhân không?" · "Gọi lại số tổng đài in trên website chính thức chưa?" |
| G2 | AI, deepfake, deepvoice, mạo danh người quen | G2.1 người thân gặp nạn cần tiền gấp; G2.2 bạn bè "đổi số mới" mượn tiền; G2.3 video call giả lãnh đạo/sếp; G2.4 cuộc gọi thu mẫu giọng | Khẩn cấp + không cho gọi lại; đổi số; nhận tiền qua tài khoản người khác | "Gọi lại số cũ đã lưu chưa?" · "Hỏi một chuyện chỉ hai người biết" · "Gia đình có mật khẩu an toàn không?" |
| G3 | Đầu tư tài chính, tuyển dụng | G3.1 việc nhẹ lương cao/CTV làm nhiệm vụ; G3.2 đầu tư chứng khoán, tiền số, ngoại hối cam kết lãi; G3.3 lãi suất "ưu đãi nội bộ" bất thường; G3.4 tình cảm rồi rủ đầu tư | Cho rút tiền nhỏ trước; cam kết lợi nhuận; nạp để "mở khóa" | "Có công ty nào trả tiền để bạn nạp tiền trước không?" · "Sàn có giấy phép ở Việt Nam không?" |
| G4 | Mua bán, giao dịch trực tuyến | G4.1 bill chuyển khoản giả; G4.2 đặt cọc phòng, vé, hàng; G4.3 shipper giả thu phí; G4.4 trúng thưởng, quà tặng phải nộp phí; G4.5 hoàn tiền đơn hàng | Áp lực thời gian; tài khoản nhận là cá nhân khác tên shop; ảnh bill không khớp tiền về | "Tiền đã về tài khoản thật chưa (xem app ngân hàng, không xem ảnh)?" · "Tên chủ tài khoản có khớp tên shop?" |
| G5 | Đánh cắp dữ liệu, chiếm quyền thiết bị | G5.1 link giả trang đăng nhập; G5.2 QR độc; G5.3 app chứa mã độc/điều khiển từ xa; G5.4 xin OTP/mật khẩu; G5.5 khóa tài khoản mạng xã hội | Link lạ, tên miền nhái; yêu cầu OTP; yêu cầu cài app ngoài kho chính thức | "Ngân hàng không bao giờ xin OTP — bạn có đang bị xin OTP?" · "Tên miền có đúng là trang chính thức?" |

## Thủ pháp tâm lý (dùng cho `red_flags[].tactic`)

urgency (gấp) · authority (quyền lực) · secrecy (giữ bí mật) · greed (lợi nhuận) · fear (dọa) · personal_account (nhận tiền vào tài khoản cá nhân) · credential_request (xin OTP/mật khẩu) · app_install (cài app) · link (link lạ)

## Số liên hệ an toàn để gợi ý

- Khẩn cấp: gọi **113** (công an).
- Ngân hàng/ví: chỉ dùng số tổng đài in trên thẻ hoặc trên website/app chính thức. Không gọi số trong tin nhắn.
- Tra website lừa đảo: tinnhiemmang.vn (NCSC) hoặc mục tin tức trên VNeID.

## Nguồn

- Báo Pháp luật VN, 09/09/2026 — Công an Hà Nội cảnh báo 25 kịch bản lừa đảo 2026
- Nhân Dân, 28/02/2026 — Dự báo điểm nóng lừa đảo trực tuyến 2026 (đa kênh, AI hóa tấn công)
- VietNamNet, 07/01/2026 — mạo danh công an là hình thức phổ biến nhất 2025
