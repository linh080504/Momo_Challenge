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

Migration có thể chạy lại để kiểm tra. `MVP_TEST_POSTGRES_URL` chỉ trỏ tới database thử. Thử FE với hai vai demo và tạo báo cáo mẫu trước khi duyệt.

```powershell
$env:MVP_TEST_POSTGRES_URL = "postgresql://paypause_stage:$($env:PAYPAUSE_STAGE_POSTGRES_PASSWORD)@127.0.0.1:55432/paypause_stage"
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

## PostgreSQL và Supabase

Chạy [migration 001](../supabase/migrations/001_mvp.sql) bằng SQL Editor hoặc `psql`. Dùng kết nối PostgreSQL trực tiếp hoặc session pooler với TLS. API truy cập schema riêng `tkc` bằng `DATABASE_URL`. Đặt thông tin kết nối và `APP_SECRET` ổn định trong secret của nhà cung cấp. Secret thay đổi sẽ làm mất khả năng đối chiếu các định danh đã băm.

## API ở Cloud Run

1. Build từ gốc repo với `docker build -f infra/docker/api.Dockerfile -t IMAGE .` và đưa image lên Artifact Registry của đội.
2. Tạo Cloud Run service public ở region Singapore (asia-southeast1), cấu hình một instance luôn sẵn sàng trong thời gian chấm. MVP dùng một API instance để giữ rate limit và giới hạn gọi LLM.
3. Cấu hình `DATABASE_URL`, `APP_SECRET`, `ALLOWED_ORIGINS`, thông tin hai tài khoản demo, `DASHSCOPE_API_KEY` nếu dùng QwenCloud Singapore hoặc các biến `LLM_*` cho Chat Completions. Đặt `SAFE_BROWSING_KEY` nếu có quyền dùng. Dùng secret của nhà cung cấp cho key và mật khẩu, và cài giới hạn ngân sách ở phía LLM.
4. Cấu hình endpoint giám sát `/health` và đặt `APP_VERSION` theo Git SHA. API đọc `PORT` từ Cloud Run.

## Web ở Vercel

1. Tạo dự án từ repo, đặt Root Directory là `apps/web` và Node.js 24.
2. Đặt `NEXT_PUBLIC_API_URL` là URL HTTPS của API trước lúc build. Thêm origin HTTPS của web vào `ALLOWED_ORIGINS` bên API.
3. Triển khai rồi kiểm tra văn bản, ảnh chụp, đăng nhập, `/ops`, VietQR và trang chia sẻ trên điện thoại.

## Xác minh

Chạy `bash .claude/skills/deploy-runbook/scripts/smoke_test.sh <API_URL>`. Dùng tài khoản user thử luồng báo cáo, dùng tài khoản ops duyệt, rồi kiểm tra lại bằng vai user. Theo dõi độ trễ và quota trong lúc chấm. Ghi URL, kết quả và phiên bản vào `docs/STATUS.md`. Khi lỗi, chuyển về revision API và deployment web trước đó, rồi chạy lại smoke test.
