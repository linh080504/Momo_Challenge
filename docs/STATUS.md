# Nhật ký trạng thái

Mỗi ngày thêm một mục ở cuối bằng `/daily-standup <ngày>`. Không sửa mục của ngày trước.

## Ngày 0 — cài bộ kit
- Đã xong: thêm bộ kit vào repo, chạy `python3 tests/test_kit_scripts.py`
- Việc ngày mai: G0 — chốt brief, taxonomy, 50 mẫu, repo + CI

## Ngày 1 — 2026-11-24 · chốt đề (hướng tới G0 21:00)

**Đã xong (có bằng chứng)**
- PM: `docs/PRODUCT_BRIEF.md` đủ 7 mục. Persona chính = người giao dịch online 20–40 (50+ là phụ). Luồng demo chính = **ảnh chụp tin nhắn**, 6 bước. **Must 7 mục** (thêm M7 tra bằng chứng: blacklist + `domain_check` + Safe Browsing). Should: S1 QR sạch, S2 link chia sẻ tóm tắt 2 câu (bot Telegram → Could). Mục 1 có 2 số liệu kèm nguồn (Bộ Công an/VietNamNet 6.000 tỷ 11T/2025; SIMO/CafeF 28/9/2026).
- PM: `docs/DECISIONS.md` +19 dòng. `docs/TASKS.md` mới: chia việc ngày 2 + hợp đồng nối việc.
- eval-qa: **`run_eval.py` gửi được ảnh** dạng `{text, image_base64, image_mime}`, báo cáo tách `p95_text`/`p95_image`. Bằng chứng: **16 test pass** (`tests/test_kit_scripts.py`).
- PM: sửa 4 chỗ lệch do đổi mốc p95 — `.claude/skills/gate-check/SKILL.md` (p95 6s/12s), `.claude/hooks/session-context.sh` (`p95_text`/`p95_image`), đường dẫn `.claude/skills/eval-harness/dataset-guide.md`, `CLAUDE.md` thêm dòng Windows.
- PM xác nhận 4 điểm eval-qa đề xuất: bỏ `image_url` · p95 tách 6/12s · ảnh hỏng trả 4xx không trả `low` · `transcript` không gửi analyzer.

**Quyết định lớn trong ngày**
- Mốc độ trễ **tách theo loại đầu vào**: văn bản p95 ≤ 6s, ảnh p95 ≤ 12s (thay cho 8s chung).
- `POST /v1/analyze` dùng **JSON base64, KHÔNG multipart**; ảnh ≤ 5 MB; 413/415 kèm thông báo tiếng Việt.
- FE **nén ảnh ở trình duyệt** (cạnh dài ≤ 1600px, JPEG) trước khi gửi.
- Nối việc bằng **stub `analyze(text, image, mime)`** commit trước **10:00 ngày 2**, không nối bằng tài liệu.
- Rủi ro #1 toàn dự án: sập/hết quota lúc BGK thử → bắt buộc có "chế độ hạn chế" (ngày 11).

**Còn nợ của G0 (chưa có bằng chứng, chốt trước 21:00)**
- AI: taxonomy đối chiếu 25 kịch bản + `prompts/analyzer_v0.md`
- BE: repo + CI xanh + `.env.example`
- FE: 3 màn tĩnh chạy local
- QA: ≥ 50 mẫu trong `eval/dataset.jsonl`

**Việc ngày mai (chi tiết: `docs/TASKS.md`)**
- Mục tiêu duy nhất: URL public → tải 1 ảnh chụp tin nhắn → kết quả đúng schema trên thẻ, < 10 giây.
- Giờ cứng: 09:30 xác nhận hợp đồng · **10:00 stub `analyze()`** · 14:00 URL API staging.

---

## `/gate-check G0` — 2026-11-24 · KẾT LUẬN: **CHƯA ĐẠT** (1/4 tiêu chí PASS)

Người kiểm: gate-check (độc lập, chỉ tính bằng chứng chạy được).

| Tiêu chí | PASS/FAIL | Bằng chứng |
|---|---|---|
| `docs/PRODUCT_BRIEF.md` đủ: vấn đề, persona, luồng chính, Must, chỉ số, ngoài phạm vi | **PASS** | Đọc file (162 dòng, sửa 19:47): §1 vấn đề có 2 số liệu kèm link nguồn · §2 bảng 3 persona (P1 chính) · §3 luồng 6 bước BGK tự thử · §4 Must M1–M7 + Should S1/S2 + Could + **Won't (ngoài phạm vi)** · §5 chỉ số có cổng số (recall ≥ 0.90, FPR ≤ 0.10, p95 văn bản ≤ 6s / ảnh ≤ 12s, ≥ 10 người thật) · §6 câu hỏi BTC · §7 rủi ro R1–R6 |
| `.claude/skills/scam-analyzer/taxonomy.md` đã đối chiếu 25 kịch bản (hoặc ghi rõ chưa tìm được) | **FAIL** | `stat` → mtime `18:09:21` = **y nguyên giờ cài bộ kit**, không có một lần sửa nào trong ngày 1. Dòng 5 vẫn là câu của bộ kit: "**Việc của ngày 1:** tìm thông báo gốc, đối chiếu và bổ sung đủ 25 mã kịch bản" → việc chưa làm, không phải kết luận "chưa tìm được". Đếm mã kịch bản con: G1=6, G2=4, G3=4, G4=5, G5=5 → **24 mã, thiếu 1**. Không có `prompts/analyzer_v0.md` (thư mục `prompts/` không tồn tại). Khớp với dòng "còn nợ" do chính STATUS ghi. |
| Repo, CI, tài khoản dịch vụ đã tạo; `.env.example` có đủ biến | **FAIL** | **Repo: KHÔNG CÓ** — `git status` → `fatal: not a git repository`; `git remote -v` cùng lỗi. README dòng 52–53 yêu cầu `git init` — chưa chạy. **CI: KHÔNG CÓ** — `find` toàn repo không thấy `.github/`, `*.yml`, `*.yaml`; không có `package.json`, `*.toml`. **Tài khoản dịch vụ: không có bằng chứng** (không có `apps/`, `infra/`, không URL nào trong STATUS). `.env.example` **đạt**: 8 biến khớp đúng danh sách `.claude/skills/deploy-runbook/SKILL.md:19` + `ANALYZER_URL`. |
| ≥ 50 mẫu dữ liệu đầu tiên (đã ẩn danh) trong `eval/` | **FAIL** | `eval/dataset.jsonl` **không tồn tại**. Chỉ có `eval/dataset.example.jsonl` = **18 dòng**, `source: "synthetic-example"`, `synthetic: true` 18/18, mtime `18:09:20` (file mẫu của bộ kit, không phải dữ liệu đội thu). 18 < 50. Không có `eval/raw-notes/`, không có `eval/images/`. |

**Bằng chứng phụ (không thuộc cổng, đã kiểm):** `py -3 tests/test_kit_scripts.py` → **16/16 OK, exit 0** (xác nhận đúng việc eval-qa báo). Báo cáo baseline `eval/reports/20261124-184758-baseline.md` có thật nhưng chạy trên 18 mẫu mẫu: recall 0.917, FPR 0.167, p95 ảnh n=0 → tự ghi "CHƯA ĐẠT". Chưa có `eval/reports/latest.json` (`run_eval.py:236` chỉ ghi khi `passed` và không `--baseline`) → `/gate-check G2` sẽ không đọc được số.

**Việc phải làm cho từng FAIL**

| # | Việc cụ thể | Người phụ trách | Xong khi |
|---|---|---|---|
| F1 | `git init` tại gốc, commit bộ kit + docs, tạo remote (GitHub) và mời cả đội; thêm CI tối thiểu `.github/workflows/ci.yml` chạy `python tests/test_kit_scripts.py` (+ `pytest apps/api` khi có); tạo & xác nhận tài khoản dịch vụ (LLM, Google Safe Browsing, Supabase, Vercel) và dán bằng chứng "key đã lấy được" vào STATUS | **backend-engineer** (PM hỗ trợ tạo repo) | URL repo + 1 lần CI xanh dán vào STATUS |
| F2 | Tìm thông báo gốc 25 kịch bản của Công an TP Hà Nội; bổ sung đủ 25 mã vào `taxonomy.md` (hiện 24) — **nếu tìm không ra thì xóa dòng 5 và ghi thẳng** "đã tìm ngày 1, không truy được bản gốc, 24 mã dưới đây do đội tổng hợp" kèm ngày + các nguồn đã thử | **ai-engineer** | `taxonomy.md` có mtime ngày 1 và một trong hai: đủ 25 mã, hoặc câu ghi rõ đã tìm không ra |
| F3 | Viết `prompts/analyzer_v0.md` từ `prompt-template.md` (món nợ G0 do PLAN ngày 1 giao, cũng là đầu vào của D2-AI-00/02) | **ai-engineer** | File tồn tại, taxonomy rút gọn đã nhúng |
| F4 | Tạo `eval/dataset.jsonl` ≥ 50 dòng hợp lệ theo `dataset-guide.md`, đã ẩn danh, không mẫu nào chứa PII thật; lưu ghi chú gốc ở `eval/raw-notes/` | **eval-qa** | `wc -l eval/dataset.jsonl` ≥ 50 + chạy được `run_eval.py --baseline` trên file đó |
| F5 | 3 màn tĩnh Next.js chạy local (`apps/web`) — PLAN ngày 1 giao, chưa có `apps/` | **frontend-engineer** | `npm run dev` mở được 3 màn, ảnh chụp khổ 390px |
| F6 | Quyết định phạm vi: F4 đang bị `D2-QA-01` (70 mẫu, 25/11 17:00) phủ lên mốc 50 mẫu của G0. Nếu chấp nhận dồn sang ngày 2 thì **ghi vào `docs/DECISIONS.md`**, không im lặng bỏ qua | **pm-lead** | Có dòng DECISIONS hoặc F4 xong trong ngày 1 |
| F7 | `.env.example` còn thiếu biến cho Must đã chốt: không có biến đăng nhập/2 tài khoản test (M6), không có URL API cho FE (ví dụ `NEXT_PUBLIC_API_URL`); `TELEGRAM_BOT_TOKEN` đã xuống Could | **backend-engineer** | Bổ sung khi dựng `apps/api`/`apps/web` ngày 2 |

**Chặn đường:** F1 chặn mọi thứ — không có repo thì không có nhánh `feat/*`, không có PR, và **hợp đồng "commit stub `analyze()` lên nhánh chung trước 10:00 ngày 2" (`docs/TASKS.md` D2-AI-00) là không thể thực hiện**. Làm F1 trước tất cả.
