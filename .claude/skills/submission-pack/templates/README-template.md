# Trước Khi Chuyển

Trợ lý AI kiểm tra tin nhắn, link, mã QR, ghi âm đáng ngờ trước khi chuyển tiền, kèm bàn làm việc để đội vận hành fintech duyệt và phát cảnh báo.

- Sản phẩm: <https://TEN-MIEN> · API: <https://api.TEN-MIEN> · Bot: @TEN_BOT
- Chủ đề: Chống lừa đảo (chính), Trợ lý AI, An ninh mạng

## Kiến trúc

(ảnh sơ đồ) — web Next.js · API FastAPI · agent phân tích (LLM + công cụ tra bằng chứng) · Postgres/pgvector · bàn làm việc vận hành

## Cấu trúc thư mục

```
apps/web     giao diện người dùng + bàn làm việc (/ops)
apps/api     API, analyzer, evidence, ops, qr
prompts/     prompt có đánh số phiên bản
eval/        bộ dữ liệu đánh giá + báo cáo
infra/       Dockerfile, cấu hình deploy
```

## Cách chạy

Yêu cầu: Node.js __, Python __, (Docker tùy chọn)

```bash
cp .env.example .env          # điền khóa API
docker compose up             # hoặc:
cd apps/api && pip install -r requirements.txt && uvicorn app.main:app --reload
cd apps/web && npm install && npm run dev
python3 .claude/skills/eval-harness/scripts/run_eval.py --data eval/dataset.jsonl --endpoint http://localhost:8000/v1/analyze
```

## Công nghệ sử dụng

| Lớp | Công nghệ |
|---|---|
| ... | ... |

## Kết quả đánh giá

Bảng chỉ số từ `eval/reports/latest.json` (ngày, số mẫu, tỷ lệ mẫu tổng hợp, recall, báo nhầm, p95).

## Tài sản có sẵn (trước cuộc thi)

- (liệt kê code, template, dataset có từ trước; ghi "Không có" nếu không có)

## Thư viện mã nguồn mở

| Thư viện | Phiên bản | License | Dùng để |
|---|---|---|---|

## Công cụ AI đã dùng

**Trong sản phẩm:** LLM (tên + phiên bản model), embedding, nhận dạng giọng nói (ví dụ PhoWhisper — VinAI, BSD-3), ...

**Hỗ trợ phát triển:** Claude Code với bộ agent/skill trong `.claude/` (liệt kê), công cụ thiết kế, ...

## Đội

| Thành viên | Vai trò |
|---|---|
