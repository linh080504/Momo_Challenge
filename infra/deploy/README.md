# Triển khai public cho MVP

## PostgreSQL và Supabase

Chạy [migration 001](../supabase/migrations/001_mvp.sql) bằng SQL Editor hoặc `psql`. Dùng kết nối PostgreSQL trực tiếp hoặc session pooler với TLS. API truy cập schema riêng `tkc` bằng `DATABASE_URL`. Đặt thông tin kết nối và `APP_SECRET` ổn định trong secret của nhà cung cấp. Secret thay đổi sẽ làm mất khả năng đối chiếu các định danh đã băm.

## API ở Cloud Run

1. Build từ gốc repo với `docker build -f infra/docker/api.Dockerfile -t IMAGE .` và đưa image lên Artifact Registry của đội.
2. Tạo Cloud Run service public ở region Singapore (asia-southeast1), cấu hình một instance luôn sẵn sàng trong thời gian chấm. MVP dùng một API instance để giữ rate limit và giới hạn gọi LLM.
3. Cấu hình `DATABASE_URL`, `APP_SECRET`, `ALLOWED_ORIGINS`, thông tin hai tài khoản demo, các biến `LLM_*` và `SAFE_BROWSING_KEY`. Dùng secret của nhà cung cấp cho key và mật khẩu, và cài giới hạn ngân sách ở phía LLM.
4. Cấu hình endpoint giám sát `/health` và đặt `APP_VERSION` theo Git SHA. API đọc `PORT` từ Cloud Run.

## Web ở Vercel

1. Tạo dự án từ repo, đặt Root Directory là `apps/web` và Node.js 24.
2. Đặt `NEXT_PUBLIC_API_URL` là URL HTTPS của API trước lúc build. Thêm origin HTTPS của web vào `ALLOWED_ORIGINS` bên API.
3. Triển khai rồi kiểm tra văn bản, ảnh chụp, đăng nhập, `/ops`, VietQR và trang chia sẻ trên điện thoại.

## Xác minh

Chạy `bash .claude/skills/deploy-runbook/scripts/smoke_test.sh <API_URL>`. Dùng tài khoản user thử luồng báo cáo, dùng tài khoản ops duyệt, rồi kiểm tra lại bằng vai user. Theo dõi độ trễ và quota trong lúc chấm. Ghi URL, kết quả và phiên bản vào `docs/STATUS.md`. Khi lỗi, chuyển về revision API và deployment web trước đó, rồi chạy lại smoke test.
