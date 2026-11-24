# Tài khoản dịch vụ ngoài

> ⛔ **TUYỆT ĐỐI KHÔNG ghi API key, token, mật khẩu, connection string vào file này.**
> File này nằm trong repo công khai khi nộp bài. Chỉ ghi **tên biến môi trường**, không ghi giá trị.
> Giá trị thật: `.env` tại máy (đã trong `.gitignore`) + secret của nhà cung cấp (Vercel/Render/GitHub Actions).

Mục đích: đóng tiêu chí "tài khoản dịch vụ đã tạo" của cổng G0, và để bất kỳ ai trong đội biết **ai giữ chìa khóa nào** khi có sự cố lúc BGK đang chấm (rủi ro R1).

Trạng thái: `chưa tạo` · `đã tạo, chưa lấy key` · `đã có key, chưa thử` · **`đã chạy thật`** (có bằng chứng gọi được)

| Dịch vụ | Chủ tài khoản | Ngày tạo | Region | Tên biến `.env` | Trạng thái |
|---|---|---|---|---|---|
| LLM chính (?) | ? | ? | ? | `LLM_API_KEY`, `LLM_MODEL` | **chờ PM điền** |
| LLM dự phòng (?) | ? | ? | ? | `LLM_FALLBACK_MODEL` | **chờ PM điền** |
| Google Safe Browsing | ? | ? | — | `SAFE_BROWSING_KEY` | **chờ PM điền** |
| Supabase | ? | ? | ? | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | **chờ PM điền** |
| Vercel (web) | ? | ? | ? | `NEXT_PUBLIC_API_URL` (biến phía web) | **chờ PM điền** |
| Hosting API (Render/Fly/khác?) | ? | ? | ? | `ALLOWED_ORIGINS`, `ANALYZER_URL` | **chờ PM điền** |
| GitHub (repo + CI) | linh080504 | 2026-11-24 | — | — (secret của Actions) | đã chạy thật — repo `linh080504/Momo_Challenge`, commit `1165717` |
| Langfuse (trace, tùy chọn) | ? | ? | ? | — | **chờ PM điền** |
| Telegram Bot | — | — | — | `TELEGRAM_BOT_TOKEN` | **không dùng vòng này** (Could, DECISIONS 2026-11-24) |

## Hai tài khoản test cho BGK (Must M6)

| Vai | Biến email | Mật khẩu để ở đâu | Trạng thái |
|---|---|---|---|
| Người dùng | `DEMO_USER_EMAIL` | secret của nhà cung cấp, **không vào repo**; dán vào PDF 1 trang lúc nộp | chưa tạo |
| Vận hành (`/ops`) | `DEMO_OPS_EMAIL` | như trên | chưa tạo |

## Quy tắc

- Ai tạo tài khoản thì là **chủ tài khoản** và phải bật 2FA.
- Mỗi dịch vụ có **ít nhất 2 người** truy cập được (tránh một người nghỉ là tắc) — ghi người thứ hai vào cột Chủ tài khoản.
- Có **hạn mức chi** thì ghi vào cột Trạng thái (ví dụ "trần 20 USD/tháng") — liên quan rủi ro R1.
- Đổi key thì cập nhật cột Ngày tạo và báo trong standup; không sửa lịch sử.
