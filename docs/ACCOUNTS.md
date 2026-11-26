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

## Cấu hình và dịch vụ cho bản nâng cấp

Thông tin dưới đây phản ánh bản local và các phụ thuộc cần chuẩn bị cho staging hoặc phát hành. Chủ dịch vụ cập nhật ngày, quyền truy cập và hạn mức khi đã xác nhận triển khai.

| Thành phần | Biến cấu hình hoặc tài nguyên | Trạng thái và việc cần chuẩn bị |
|---|---|---|
| QwenCloud Singapore | `DASHSCOPE_API_KEY`, `LLM_CALLS_PER_DAY` | Đã gọi thật `qwen4-max` trên local. Đưa key staging vào secret của máy chủ và đặt hạn mức. Để trống `LLM_BASE_URL` và `LLM_MODEL` để dùng adapter QwenCloud. |
| Chat Completions hoặc model tự vận hành | `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_FALLBACK_MODEL` | Có adapter. Chốt endpoint, model chính/dự phòng, quyền sử dụng và quota sau benchmark. |
| Google Safe Browsing và RDAP | `SAFE_BROWSING_KEY`, `RDAP_LOOKUPS_PER_HOUR` | Xác minh nguồn Safe Browsing với cấu hình staging. RDAP dùng endpoint registry cố định cho `.com` và `.net`. Mặc định hạn mức RDAP bằng 0. |
| OCR, Whisper và FraudURL cục bộ | `OCR_COMMAND`, `WHISPER_COMMAND`, `WHISPER_MODEL_PATH`, `FRAUD_URL_MODEL_PATH` | OCR đã chạy local. Chuẩn bị binary và trọng số Whisper, artifact FraudURL đã đánh giá cùng `manifest.json`. Kiểm tra quyền truy cập thư mục model. |
| Hạ tầng và tài khoản demo | `DATABASE_URL`, `APP_SECRET`, `ALLOWED_ORIGINS`, `NEXT_PUBLIC_API_URL`, `DEMO_USER_EMAIL`, `DEMO_USER_PASSWORD`, `DEMO_OPS_EMAIL`, `DEMO_OPS_PASSWORD` | Hai vai đã thử trên local. Xác nhận tài khoản demo riêng cho staging, chạy smoke test và kiểm tra CORS, phiên đăng nhập, kết nối PostgreSQL. |
| Nguồn đang xem xét | Gemini cho VLM dự phòng, nguồn giao dịch ngân hàng, email/SMS và thông báo nội bộ | Cần xác nhận chủ dự án, phạm vi được cấp quyền, hạn mức, môi trường thử và dữ liệu được phép gửi trước khi thêm biến triển khai. |

Chỉ khai báo tên biến trong `.env.example`. Lưu giá trị thật ở `.env` đã được Git bỏ qua hoặc kho secret phía máy chủ. [Việc chuẩn bị môi trường](TASKS.md#công-việc-nâng-cấp-paypause-ai)
