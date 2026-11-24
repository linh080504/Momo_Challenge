# Chia việc theo ngày — Trước Khi Chuyển

Quy ước: 1 task = 1 người sở hữu, 0.5–1 ngày, "Xong khi" kiểm chứng được, ghi rõ file được sửa.
Nhánh `feat/<vai>-<việc>`, merge qua PR. "Xong" = có bằng chứng dán vào standup.

**Ranh giới thư mục (không ai sửa ngoài phần mình):**
`apps/web/**` FE · `apps/api/**` trừ analyzer: BE · `apps/api/app/analyzer/**` + `prompts/**`: AI · `eval/**` + `.claude/skills/eval-harness/**`: QA · `docs/**`: PM · `submission/**`: pitch-writer.

---

## Ngày 1 — 2026-11-24 (đang chạy, chốt G0 21:00)

| Task | Chủ | File | Xong khi | Hạn |
|---|---|---|---|---|
| D1-QA-01 `run_eval.py` gửi ảnh | eval-qa | `.claude/skills/eval-harness/scripts/run_eval.py`, `.claude/skills/eval-harness/dataset-guide.md` | ✅ **XONG** — gửi `{text, image_base64, image_mime}`, báo cáo tách `p95_text`/`p95_image`, **16 test pass** | ✅ xong 24/11 |
| D1-PM-01 Brief + DECISIONS | pm-lead | `docs/PRODUCT_BRIEF.md`, `docs/DECISIONS.md` | ✅ Brief đủ 7 mục, mục 1 có 2 số liệu kèm nguồn | ✅ xong 24/11 |
| D1-PM-02 Sửa 4 chỗ lệch do đổi mốc p95 | pm-lead | `.claude/skills/gate-check/SKILL.md`, `.claude/hooks/session-context.sh`, `docs/PRODUCT_BRIEF.md`, `CLAUDE.md` | ✅ **XONG** — gate-check ghi "p95 văn bản ≤ 6s, ảnh ≤ 12s"; hook in `p95_text`/`p95_image`; đường dẫn `dataset-guide.md` đúng; CLAUDE.md có dòng Windows | ✅ xong 24/11 |
| D1-PM-03 Xác nhận 4 điểm của eval-qa | pm-lead | `docs/DECISIONS.md` | ✅ **XONG** — bỏ `image_url`, p95 6/12s, 4xx cho ảnh hỏng, `transcript` không gửi analyzer; cột "Người quyết" đổi thành PM | ✅ xong 24/11 |

---

## Ngày 2 — 2026-11-25 · Walking skeleton public

**Mục tiêu ngày (điều kiện duy nhất để coi là xong):** mở **URL public** trên điện thoại → **tải 1 ảnh chụp tin nhắn** → nhận kết quả JSON đúng schema hiển thị trên thẻ, **dưới 10 giây**.

| Task | Chủ | File | Xong khi | Hạn |
|---|---|---|---|---|
| **D2-BE-01** `POST /v1/analyze` | backend-engineer | `apps/api/app/api/**`, `apps/api/app/schemas/**`, `apps/api/tests/**` | Nhận **JSON base64** theo hợp đồng dưới (KHÔNG multipart), gọi `analyzer.analyze()`, **validate output theo `analysis.schema.json` trước khi trả**; test cho cả 413/415/422; `pytest` xanh; dán output `curl` cho 1 ảnh + 1 văn bản | 25/11 14:00 |
| **D2-BE-02** Deploy API 1 instance | backend-engineer | `infra/**`, `apps/api/Dockerfile`, `.env.example` | `bash .claude/skills/deploy-runbook/scripts/smoke_test.sh <API_URL>` pass; URL dán vào `docs/STATUS.md`; secret chỉ ở biến môi trường | 25/11 18:00 |
| **D2-BE-03** CI + điền `docs/ACCOUNTS.md` (nợ G0: F1b, F1c) | backend-engineer | `.github/workflows/ci.yml`, `docs/ACCOUNTS.md` | CI xanh 1 lần (chạy `tests/test_kit_scripts.py` + `pytest apps/api`); mọi dòng `ACCOUNTS.md` hết trạng thái "chờ"; **không có secret nào trong repo** (quét trước khi commit) | 25/11 12:00 |
| **D2-AI-01** Pipeline bước 1–3 | ai-engineer | `apps/api/app/analyzer/**`, `prompts/analyzer_v0.md` | 5 ảnh chụp tin nhắn thật → đọc được chữ, trích đúng STK/SĐT/tên miền, **`pii_mask` chạy trước mọi lần gọi LLM**; `grep` log không thấy STK/SĐT chưa mask | 25/11 15:00 |
| **D2-AI-00** **Stub `analyze()`** (chặn đường cả BE và FE) | ai-engineer | `apps/api/app/analyzer/__init__.py` | Commit lên nhánh chung: `analyze(text: str\|None, image: bytes\|None, mime: str\|None) -> dict` trả **JSON mẫu đúng `analysis.schema.json`**; BE import được, FE lấy được JSON đó | **25/11 10:00 — cứng** |
| **D2-AI-02** Output đúng schema + 3 dấu hiệu có trích dẫn | ai-engineer | `apps/api/app/analyzer/**`, `prompts/analyzer_v0.md` | 10/10 mẫu thử trả JSON validate schema; mỗi dấu hiệu có `quote` khớp đúng chuỗi trong đầu vào — **với ảnh là khớp văn bản đã đọc từ ảnh (OCR/vision)**; không khớp thì bỏ dấu hiệu | 25/11 19:00 |
| **D2-FE-01** Ô nhập + nén ảnh + deploy Vercel | frontend-engineer | `apps/web/app/**`, `apps/web/components/**`, `apps/web/lib/**` | 1 ô nhập nhận **dán chữ + tải ảnh**, 1 nút chính "Kiểm tra", chữ ≥ 18px; **nén ảnh ở trình duyệt: cạnh dài ≤ 1600px, JPEG, rồi base64** — dán log kích thước trước/sau cho 1 ảnh điện thoại (phải < 5 MB); deploy Vercel, URL vào STATUS | 25/11 16:00 |
| **D2-FE-02** Thẻ kết quả đọc JSON | frontend-engineer | `apps/web/components/**` | Hiển thị mức nguy cơ + 3 dấu hiệu + trích dẫn + câu hỏi kiểm chứng + **câu "Kết quả do AI phân tích và có thể sai…"**; đọc JSON mẫu không cần API; ảnh chụp khổ 390px | 25/11 20:00 |
| **D2-QA-01** 70 mẫu dataset (đã gộp mốc 50 mẫu của G0) | eval-qa | `eval/dataset.jsonl`, `eval/raw-notes/**` | 70 dòng hợp lệ theo `.claude/skills/eval-harness/dataset-guide.md`, **≥ 10 mẫu có `image`**, đã ẩn danh; không mẫu nào chứa PII thật | 25/11 17:00 |
| **D2-QA-01a** 🚩 **Điều kiện của nhượng bộ F6** | eval-qa | `eval/dataset.jsonl` | **≥ 30 mẫu THẬT** (`synthetic: false`) đã nằm trong `dataset.jsonl` và báo trong nhóm. **Trượt mốc này → PM cắt phạm vi ngay trong buổi chiều**, không chờ 17:00 | **25/11 12:00 — cứng** |
| **D2-QA-02a** `last_run.json` luôn được ghi | eval-qa | `.claude/skills/eval-harness/scripts/run_eval.py` | `run_eval.py` **luôn** ghi `eval/reports/last_run.json` dù đạt cổng hay không, dù có `--baseline` hay không; `latest.json` giữ nghĩa "lần đạt cổng gần nhất". Bằng chứng: 1 lần chạy trượt cổng vẫn sinh ra `last_run.json` + test mới pass | 25/11 15:00 |
| **D2-QA-04** Mẫu thật cho G1.7 | eval-qa | `eval/dataset.jsonl`, `eval/raw-notes/**` | **≥ 2 mẫu thật** (không `synthetic`) gắn `scenario_id: "G1.7"` — mạo danh bệnh viện/nhà trường báo cấp cứu hoặc đóng phí gấp; đã ẩn danh | 25/11 17:00 |
| **D2-QA-03** Test ảnh hỏng / quá cỡ | eval-qa | `eval/adversarial-d2.md` | 4 ca: ảnh 6 MB · `image/gif` · base64 hỏng · chỉ có `text: ""` → đều trả 4xx kèm thông báo tiếng Việt, **không ca nào trả `low`** | 25/11 21:00 |
| **D2-QA-02** Eval baseline "không có AI" | eval-qa | `eval/reports/**` | `run_eval.py --baseline --tag baseline` chạy xong, báo cáo trong `eval/reports/`; dán bảng recall/báo nhầm làm mốc so sánh | 25/11 20:00 |
| **D2-PM-01** Chốt hợp đồng + STATUS | pm-lead | `docs/TASKS.md`, `docs/STATUS.md` | BE + AI + FE xác nhận hợp đồng JSON base64 bằng tin nhắn trước 09:30; kiểm stub có mặt lúc 10:00; STATUS chốt trước 22:00 | 25/11 22:00 |

### Hợp đồng nối việc ngày 2 (chốt trước 10:00, đổi phải ghi DECISIONS)

**Ranh giới BE ↔ AI** — BE không viết logic phân tích, AI không viết endpoint. **Nối bằng stub, không bằng tài liệu:**

```
# apps/api/app/analyzer/__init__.py  — AI sở hữu, BE chỉ gọi
async def analyze(text: str | None, image: bytes | None, mime: str | None) -> dict
# trả dict đúng .claude/skills/scam-analyzer/analysis.schema.json
# raise AnalyzerError(code, message) khi fail — BE map thành HTTP 502 + body có 'error'
```

**Ranh giới BE ↔ FE** — JSON base64, KHÔNG multipart (khớp `run_eval.py`):

```
POST /v1/analyze   Content-Type: application/json
{
  "text": "",                                  # str, "" nếu chỉ có ảnh
  "image_base64": "...",                       # tùy chọn
  "image_mime": "image/png" | "image/jpeg"     # tùy chọn, bắt buộc nếu có image_base64
}
# phải có ít nhất 1 trong text (khác "") hoặc image_base64. Ảnh ≤ 5 MB byte gốc.
200 → body đúng analysis.schema.json
413 → ảnh quá cỡ        · 415 → mime không hỗ trợ
422 → thiếu cả hai đầu vào · 502 → analyzer lỗi
```

Hai trường tùy chọn đã chốt (DECISIONS 2026-11-24): `locale` **tùy chọn, mặc định `"vi"`** — **thiếu `locale` không được trả 422** vì `run_eval.py` không gửi trường này; `url` **nhận nhưng chưa dùng đến ngày 3**. `audio_url` đã bỏ khỏi hợp đồng.

⚠️ **Mọi lỗi ảnh phải trả 4xx kèm thông báo tiếng Việt. TUYỆT ĐỐI không trả `risk_level: "low"` cho ảnh không đọc được** — người dùng sẽ hiểu là "an toàn" và chuyển tiền.

**Thứ tự mở khóa trong ngày 2 (ai nợ ai, giờ cứng):**

| Giờ | Món | Chủ | Mở khóa cho |
|---|---|---|---|
| **10:00** | Stub `analyze()` commit lên nhánh chung (D2-AI-00) | ai-engineer | BE nối endpoint · FE lấy JSON mẫu |
| **14:00** | URL API staging chạy được (kể cả còn trả stub) | backend-engineer | FE gọi API thật |
| sau đó | AI thay ruột thật vào stub | ai-engineer | — (không ai phải chờ) |

### Ghi chú ngày 2

- Mốc "< 10 giây" của ngày 2 chỉ là **1 ảnh, 1 lần**. Mốc chính thức **p95 ≤ 6s văn bản / ≤ 12s ảnh** áp từ ngày 4, khi đã có đủ mẫu.
- Ngày 2 **chưa** làm tiến trình chờ 3 chặng (đó là việc ngày 4) — ngày 2 chỉ cần spinner.
- Ngày 2 **chưa** tra bằng chứng bên ngoài (ngày 3).
- Nếu đến 18:00 analyzer chưa chạy ổn: **cắt D2-AI-02 sang ngày 3**, giữ bằng mọi giá mục tiêu "ảnh → kết quả trên URL public" (stub vẫn cho demo được luồng).
- **Nếu stub trễ sau 10:00:** PM tự commit stub từ `prompts/sample_output.json` để BE/FE không đứng — việc này được phép vượt ranh giới thư mục, ghi vào STATUS.

---

## Các ngày sau

Xem `docs/PLAN.md` (đã nhúng 7 task phát sinh từ brief vào ngày 1, 3, 4, 9, 11). File này chỉ chia chi tiết cho ngày đang chạy và ngày kế tiếp; PM cập nhật mỗi tối sau standup.
