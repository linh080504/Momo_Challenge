# Triển khai public cho MVP

## Staging PostgreSQL trên máy phát triển

Dùng `compose.staging.yaml` cùng `compose.yaml` để thử bản triển khai với PostgreSQL riêng. Tệp hợp nhất cổng bằng `!override` của Docker Compose. Database có volume riêng và tự áp migration khi khởi tạo. Web nghe ở `127.0.0.1:3020`, API ở `127.0.0.1:8020` và PostgreSQL ở `127.0.0.1:55432`. [Docker Compose merge](https://docs.docker.com/reference/compose-file/merge/)

Trong PowerShell, dùng mật khẩu URL-safe riêng cho database thử và một `APP_SECRET` staging riêng dài ít nhất 32 ký tự. Giữ cả hai ổn định qua các lần chạy cùng volume. Cấu hình dịch vụ và hai vai demo lấy từ `.env` ở gốc repo.

```powershell
$env:PAYPAUSE_STAGE_POSTGRES_PASSWORD = '<staging-password>'
$env:PAYPAUSE_STAGE_APP_SECRET = '<staging-app-secret>'
$env:PAYPAUSE_STAGE_VERSION = "$(git rev-parse --short HEAD)-working-tree"
docker compose -p paypause-stage -f compose.yaml -f compose.staging.yaml up -d --build --wait
Invoke-RestMethod http://127.0.0.1:8020/health
```

Volume đã khởi tạo cần áp các migration mới thủ công. `MVP_TEST_POSTGRES_URL` chỉ trỏ tới database thử. Thử FE với hai vai demo và tạo báo cáo mẫu trước khi duyệt.

```powershell
$env:MVP_TEST_POSTGRES_URL = "postgresql://paypause_stage:$($env:PAYPAUSE_STAGE_POSTGRES_PASSWORD)@127.0.0.1:55432/paypause_stage"
Get-Content -Raw infra/supabase/migrations/002_sample_reviews.sql | docker compose -p paypause-stage -f compose.yaml -f compose.staging.yaml exec -T postgres psql -U paypause_stage -d paypause_stage -v ON_ERROR_STOP=1
.\.venv\Scripts\python.exe -m pytest -q
```

Đo baseline kỹ thuật với tập tổng hợp bằng lệnh sau. Báo cáo nằm trong `eval/generated/stage-baseline`. Lưu cấu hình provider, phiên bản và số mẫu cùng kết quả so sánh.

```powershell
.\.venv\Scripts\python.exe eval/prepare_smoke.py
.\.venv\Scripts\python.exe .claude/skills/eval-harness/scripts/run_eval.py --data eval/generated/dataset.smoke.jsonl --endpoint http://127.0.0.1:8020/v1/analyze --tag stage-smoke --out eval/generated/stage-baseline
```

### Bật nhận dạng ghi âm ở staging

Chọn trọng số GGML đa ngôn ngữ đã xác minh checksum. Tệp cấu hình mở rộng build `whisper-cli` từ bản `v1.9.6`, gắn trọng số chỉ đọc và phiên âm trên máy chủ ứng dụng. Dùng `base-q5_1` cho smoke nhẹ và thử `large-v3-turbo` để đánh giá chất lượng. [whisper.cpp](https://github.com/ggml-org/whisper.cpp/releases/tag/v1.9.6) · [Trọng số GGML](https://huggingface.co/ggerganov/whisper.cpp)

```powershell
$env:PAYPAUSE_WHISPER_MODEL_FILE = (Resolve-Path '<local-ggml-model.bin>').Path
docker compose -p paypause-stage -f compose.yaml -f compose.staging.yaml -f compose.speech.yaml up -d --build --wait
```

### Bật ảnh chụp website trên preview cục bộ

Preview cục bộ có thể bật `WEBSITE_CAPTURE_ENABLED=true` cho API sau khi cài Playwright Python và Chromium bằng `python -m playwright install chromium`. Tính năng chụp dùng HTML và tài nguyên đã duyệt cho bài viết trong danh mục. Khi Chromium không khả dụng, báo cáo dùng ảnh minh họa nếu lấy được.

Đặt `WEBSITE_PUBLIC_HTML_ENABLED=true` để phân tích HTML ngoài danh mục. API phân giải tên miền qua Cloudflare DNS, kết nối trực tiếp đến địa chỉ công khai đã kiểm tra và giới hạn thời gian, kích thước và cổng kết nối. Môi trường triển khai nên chặn mạng nội bộ ở tầng egress. Khi bật thêm `WEBSITE_CAPTURE_ENABLED`, Chromium dựng và chụp bản HTML đã tải trong ngữ cảnh offline. Môi trường thiếu Chromium vẫn trả phân tích nội dung.

## PostgreSQL và Supabase

Chạy [migration 001](../supabase/migrations/001_mvp.sql) và [migration 002](../supabase/migrations/002_sample_reviews.sql) theo thứ tự bằng SQL Editor hoặc `psql`. Dùng kết nối PostgreSQL trực tiếp hoặc session pooler với TLS. API truy cập schema riêng `tkc` bằng `DATABASE_URL`. Đặt thông tin kết nối và `APP_SECRET` ổn định trong secret của nhà cung cấp. Secret thay đổi sẽ làm mất khả năng đối chiếu các định danh đã băm.

## API ở Cloud Run

1. Build từ gốc repo với `docker build -f infra/docker/api.Dockerfile -t IMAGE .` và đưa image lên Artifact Registry của đội.
2. Tạo Cloud Run service public ở region Singapore (asia-southeast1), cấu hình một instance luôn sẵn sàng trong thời gian chấm. MVP dùng một API instance để giữ rate limit và giới hạn gọi LLM.
3. Cấu hình `DATABASE_URL`, `APP_SECRET`, `ALLOWED_ORIGINS`, thông tin hai tài khoản demo và `DASHSCOPE_API_KEY` cho Qwen4-Max tại Singapore. Đặt `SAFE_BROWSING_KEY` nếu có quyền dùng. Lưu key và mật khẩu trong secret của nhà cung cấp. `LLM_CALLS_PER_DAY` dùng chung cho Deep Path và `/ops`, mỗi lần chạy đủ bàn điều tra dùng tối đa bảy lượt.
4. Cấu hình endpoint giám sát `/health` và đặt `APP_VERSION` theo Git SHA. API đọc `PORT` từ Cloud Run.

## Web ở Vercel

1. Tạo dự án từ repo, đặt Root Directory là `apps/web` và Node.js 24.
2. Đặt `NEXT_PUBLIC_API_URL` là URL HTTPS của API trước lúc build. Thêm origin HTTPS của web vào `ALLOWED_ORIGINS` bên API.
3. Triển khai rồi kiểm tra văn bản, ảnh chụp, đăng nhập, `/ops`, VietQR và trang chia sẻ trên điện thoại.

## Xác minh

Chạy `bash .claude/skills/deploy-runbook/scripts/smoke_test.sh <API_URL>`. Kiểm tra `/health` cho tiến trình và `/ready` cho kết nối cơ sở dữ liệu. Dùng tài khoản user thử luồng báo cáo, dùng tài khoản ops gán nhãn, duyệt rồi kiểm tra lại bằng vai user. `/v1/ops/system` hiển thị phiên bản prompt, tri thức và tình trạng cấu hình nguồn mà không trả giá trị khóa. Đối chiếu số lỗi, p95 và tỷ lệ kết quả hạn chế trong báo cáo eval. Khi lỗi sau phát hành, quay về ảnh API và bản web trước đó, giữ secret và dữ liệu đã lưu, rồi chạy lại smoke. Migration 002 chỉ bổ sung bảng nên bản cũ vẫn đọc được những bảng đã có.
