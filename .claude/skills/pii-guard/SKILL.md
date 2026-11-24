---
name: pii-guard
description: "Bảo vệ dữ liệu cá nhân và tuân thủ pháp lý cho sản phẩm — ẩn danh SĐT, số tài khoản, thẻ, CCCD, OTP, email trước khi gửi LLM; quy tắc lưu trữ, đồng ý, xóa dữ liệu theo Luật BVDLCN 2025; gắn nhãn nội dung AI theo Luật AI 2025. Dùng khi viết code gửi dữ liệu người dùng ra ngoài (LLM, API bên thứ ba), khi thiết kế bảng DB, log, hoặc màn hình đồng ý."
allowed-tools: Bash(python3 .claude/skills/pii-guard/scripts/pii_mask.py *)
---

# PII guard

## Ẩn danh trước khi gửi LLM (bắt buộc)

```bash
python3 .claude/skills/pii-guard/scripts/pii_mask.py --json "Chuyển 5.000.000đ vào STK 0123456789, gọi 0912 345 678"
```

- Trả `masked` (gửi LLM), `mapping` (chỉ giữ trong bộ nhớ server), `entities` (hash để tra danh sách đen).
- Số tiền giữ nguyên. Cùng giá trị → cùng token.
- Trong backend: port `Masker` sang module `app/privacy/mask.py`, viết test cho các mẫu mới gặp.

## Quy tắc dữ liệu

| Loại | Lưu? | Thời hạn | Ghi chú |
|---|---|---|---|
| Văn bản/ảnh người dùng gửi | Chỉ khi người dùng đồng ý "đóng góp để bảo vệ người khác" | 30 ngày | Mặc định xử lý xong là xóa |
| Ghi âm | Không lưu | Xóa ngay sau khi bóc băng | |
| Hash thực thể (STK, SĐT, URL) | Có | Theo vòng đời báo cáo | Không lưu giá trị gốc trong bảng tra cứu |
| Log hệ thống | Có, đã mask | 14 ngày | Không log mapping, không log ảnh |

- Màn hình đầu tiên: một câu giải thích dữ liệu dùng để làm gì + nút đồng ý; nút "Xóa dữ liệu của tôi" trong cài đặt.
- Không gửi dữ liệu chưa mask cho bên thứ ba. Khóa API để ở biến môi trường, không commit.

## Minh bạch theo Luật AI

- Luật Trí tuệ nhân tạo số 134/2025/QH15 có hiệu lực từ 01/03/2026; Nghị định 142/2026/NĐ-CP (Điều 18) quy định thông báo, gắn nhãn nội dung do AI tạo.
- Mỗi kết quả hiển thị: "Kết quả do AI phân tích và có thể sai. Hãy xác minh qua số tổng đài chính thức." (trường `ai_disclaimer` trong schema).
- Người dùng phải biết họ đang trò chuyện với AI (bot Telegram ghi rõ ở tin chào).
- Chi tiết và nguồn: `compliance.md`.
