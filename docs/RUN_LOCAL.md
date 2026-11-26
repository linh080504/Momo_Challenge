# Chạy API local (Windows)

PayPause AI dùng `app.main:app` cho web mặc định, Qwen, PostgreSQL và bàn vận hành. Phần còn lại của tài liệu mô tả API ngày 2, chạy bằng `app.day_two:create_app` và có thể thử giao diện tại `/prototype`. [Chạy PayPause AI](../README.md#chạy-mvp-trên-máy) · [Staging PostgreSQL](../infra/deploy/README.md#staging-postgresql-trên-máy-phát-triển)

Lệnh dưới đây dùng PowerShell và launcher `py -3` (Python 3.12). Chạy từ **gốc repo** trừ khi ghi khác. Không deploy gì cả — mọi thứ chạy trên máy bạn.

## 1. Cài thư viện (một lần)

```powershell
py -3 --version                       # cần Python 3.10 trở lên (đã thử với 3.12)
py -3 -m venv .venv                   # tuỳ chọn nhưng nên dùng; .venv/ đã nằm trong .gitignore
.\.venv\Scripts\Activate.ps1          # nếu bị chặn: Set-ExecutionPolicy -Scope Process Bypass
py -3 -m pip install -r apps/api/requirements-dev.txt
```

Sau khi kích hoạt venv, `py -3` vẫn dùng được (nó chọn Python của venv). Không kích hoạt venv thì thay bằng `.\.venv\Scripts\python.exe`.

## 2. Chạy API

**Bước 2a — tạo `.env` và khoá băm (một lần).** `ENTITY_HASH_KEY` là biến **bắt buộc duy nhất**: thiếu hoặc ngắn hơn 32 ký tự thì API từ chối khởi động (cố ý — hash ghi bằng khoá tạm sẽ không sửa lại được).

```powershell
Copy-Item .env.example .env
py -3 -c "import secrets; print(secrets.token_hex(32))"
```

Mở `.env`, dán chuỗi vừa in ra sau `ENTITY_HASH_KEY=` (không có dấu cách, không có dấu nháy). `.env` đã nằm trong `.gitignore` — không commit. **Giữ nguyên khoá này**: đổi khoá thì mọi hash đã lưu mất tác dụng. Xoá `apps\api\data\tkc.db` nếu lỡ đổi khoá trong lúc dev.

**Bước 2b — chạy server:**

```powershell
cd apps\api
py -3 -m uvicorn app.day_two:create_app --factory --port 8000 --env-file ..\..\.env
```

- **Phải đứng ở `apps\api`** (nếu không sẽ báo `ModuleNotFoundError: No module named 'app'`).
- `--factory` là bắt buộc: ứng dụng được tạo bởi hàm `create_app()`, không có biến `app` ở cấp module.
- Không dùng `.env` thì đặt biến trong phiên: `$env:ENTITY_HASH_KEY = "<chuỗi ≥ 32 ký tự>"`, rồi bỏ `--env-file ..\..\.env`.
- Muốn tự nạp lại khi sửa code, thêm `--reload` (chưa thử trong phiên làm việc này).
- Dừng server: `Ctrl+C`.
- Mặc định web (Next.js) ở `http://localhost:3000` được phép gọi API (CORS). Muốn thêm origin: đặt `ALLOWED_ORIGINS` (cách nhau bằng dấu phẩy).
- Tài liệu API tương tác (thử trực tiếp trên trình duyệt): <http://localhost:8000/docs>

## 3. Thử nhanh

```powershell
curl.exe -s http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}
```

> Trong PowerShell, `curl` là bí danh của `Invoke-WebRequest`. Luôn gõ **`curl.exe`**. Với JSON tiếng Việt, ghi body ra file rồi dùng `--data-binary "@file"` để khỏi vướng dấu nháy và mã hoá.

**Văn bản**

```powershell
'{"text": "Tôi là cán bộ công an, anh chuyển tiền vào tài khoản tạm giữ để xác minh, không được nói với ai."}' |
  Set-Content -Encoding utf8 body_text.json
curl.exe -s -H "Content-Type: application/json" --data-binary "@body_text.json" http://localhost:8000/v1/analyze
```

**Ảnh chụp tin nhắn** (PNG hoặc JPEG, ≤ 5 MB; web sẽ tự nén, ở đây bạn tự đưa ảnh nhỏ vào)

```powershell
$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("anh.png"))
@{ text = ""; image_base64 = $b64; image_mime = "image/png" } | ConvertTo-Json |
  Set-Content -Encoding utf8 body_img.json
curl.exe -s -H "Content-Type: application/json" --data-binary "@body_img.json" http://localhost:8000/v1/analyze
```

**Đọc mã VietQR**

```powershell
'{"payload": "<chuỗi giải mã từ mã QR>"}' | Set-Content -Encoding utf8 body_qr.json
curl.exe -s -H "Content-Type: application/json" --data-binary "@body_qr.json" http://localhost:8000/v1/qr/parse
```

**Báo cáo** (`consent_contribute` mặc định `false` = chỉ lưu hash thực thể, không lưu nội dung)

```powershell
'{"text": "Chuyển vào STK 0123456789, gọi 0912 345 678", "consent_contribute": false}' |
  Set-Content -Encoding utf8 body_report.json
curl.exe -s -H "Content-Type: application/json" --data-binary "@body_report.json" http://localhost:8000/v1/reports
```

Mã lỗi của `/v1/analyze`: `413` ảnh quá 5 MB · `415` ảnh sai định dạng (chỉ PNG/JPEG) hoặc hỏng · `422` thiếu cả chữ lẫn ảnh, hoặc chữ dài quá 10.000 ký tự · `429` gửi quá nhanh · `502` analyzer lỗi hoặc quá 25 giây. Analyzer tự báo `empty_input`/`unsupported_mime`/`image_too_large` thì cũng ra `422`/`415`/`413` như trên. Mọi lỗi có dạng `{"error": "<thông báo tiếng Việt>", "code": "<mã>"}` và **không bao giờ** trả `risk_level`.

## 4. Chạy test

```powershell
py -3 -m pytest apps/api              # test API (không cần mạng, không cần analyzer thật)
py -3 tests/test_kit_scripts.py       # test bộ kit (CI chạy cả hai)
```

Test giả lập `analyzer.analyze()` bằng monkeypatch nên chạy được dù chưa có analyzer. DB test là SQLite trong thư mục tạm.

## 5. Analyzer

`POST /v1/analyze` gọi `app.analyzer.analyze()` do ai-engineer viết (nhánh `feat/d2-analyzer`). **Khi nhánh bạn đang chạy chưa có `apps/api/app/analyzer/`, endpoint trả `502` `analyzer_unavailable`** — cố ý trả lỗi thật chứ không trả kết quả giả. Merge/rebase nhánh có stub analyzer là chạy được, không cần cấu hình thêm.

## 6. Cơ sở dữ liệu

- Mặc định: SQLite tại `apps\api\data\tkc.db` (tự tạo, đã ignore). Xoá file này để làm lại từ đầu.
- Bảng `entities`, `reports`, `report_entities` được tạo tự động lúc khởi động. Chưa có migration (Alembic) — khi đổi cột sau khi đã có dữ liệu thật mới cần.
- Sang Postgres/Supabase **chỉ đổi biến môi trường**: cài driver (`py -3 -m pip install psycopg2-binary`) rồi đặt `DATABASE_URL=postgresql://user:password@host:5432/dbname` (dạng `postgres://` cũng được). Không sửa code.

## 7. Biến môi trường của API

Chỉ `ENTITY_HASH_KEY` là bắt buộc; còn lại để trống = dùng mặc định. Danh sách đầy đủ có chú thích: `.env.example`.

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `ENTITY_HASH_KEY` | **không có — bắt buộc** | Khoá HMAC-SHA256 (≥ 32 ký tự) để băm SĐT/STK/tên miền. Thiếu → API không khởi động |
| `LLM_PROVIDER`, `LLM_FALLBACK_PROVIDER`, `PROMPTS_DIR` | trống | Do **analyzer** đọc (không phải phần BE): `LLM_PROVIDER` trống/`none` = chế độ hạn chế (luật + danh sách đen), `mock` = offline để tích hợp. `PROMPTS_DIR` chỉ cần khi image deploy không có thư mục `prompts/` |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Origin được gọi API (CORS) |
| `DATABASE_URL` | SQLite `apps/api/data/tkc.db` | Chuỗi kết nối DB |
| `APP_VERSION` / `GIT_SHA` | `0.1.0` | Version trả về ở `/health` |
| `ANALYZE_TIMEOUT_SECONDS` | `25` | Quá hạn này → `502 analyzer_timeout` |
| `RATE_LIMIT_ANALYZE_PER_MIN` | `20` | Số request `/v1/analyze` mỗi IP mỗi 60 giây |
| `RATE_LIMIT_REPORTS_PER_MIN` | `10` | Như trên cho `/v1/reports` |
| `RATE_LIMIT_DEFAULT_PER_MIN` | `60` | Như trên cho các `/v1/*` còn lại. `/health` không bị giới hạn |
| `TRUSTED_PROXY_COUNT` | `0` | Số proxy tin cậy đứng trước API. Để `0` khi chạy local |
| `ANALYSIS_SCHEMA_PATH`, `VIETQR_SCRIPT_PATH` | file trong `.claude/skills/` | Chỉ đổi khi image deploy không có thư mục `.claude/` |

## 8. Lỗi thường gặp

| Triệu chứng | Cách xử lý |
|---|---|
| `ValueError: ENTITY_HASH_KEY chưa đặt hoặc quá ngắn` | Làm bước 2a; kiểm tra dòng trong `.env` không có dấu cách/nháy và đã truyền `--env-file` |
| `ModuleNotFoundError: No module named 'app'` | Chưa `cd apps\api` |
| `Attribute "app" not found in module "app.main"` | Thiếu `--factory` |
| `py` không nhận ra | Cài Python từ python.org (tick "py launcher") hoặc dùng `python` |
| Trình duyệt báo CORS | Origin của web không có trong `ALLOWED_ORIGINS`; kiểm tra đúng cổng và `http` / `https` |
| Gọi mãi bị `429` | Chạm rate limit theo IP; đợi theo header `Retry-After` hoặc tăng `RATE_LIMIT_*` khi dev |
| `502` `analyzer_unavailable` | Nhánh hiện tại chưa có `app/analyzer` (xem mục 5) |
| `Address already in use` | Đổi `--port 8001` (nhớ đổi `NEXT_PUBLIC_API_URL` của web) |
