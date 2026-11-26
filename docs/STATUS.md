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

---

## `/gate-check G0` (lần 2) — 2026-11-24 20:10 · KẾT LUẬN: **CHƯA ĐẠT** (1/4 tiêu chí PASS)

Người kiểm: gate-check (độc lập, kiểm lại từ đầu, không tin lời tự báo cáo).
**Thay đổi duy nhất so với lần 1 (19:57):** repo git đã được tạo và đẩy lên GitHub. Ba tiêu chí FAIL còn lại chưa có chuyển động nào.

| Tiêu chí | PASS/FAIL | Bằng chứng |
|---|---|---|
| `docs/PRODUCT_BRIEF.md` đủ: vấn đề, persona, luồng chính, Must, chỉ số, ngoài phạm vi | **PASS** | Đọc file (163 dòng, mtime `19:47:20`): §1 vấn đề + 2 số liệu kèm link nguồn · §2 bảng 3 persona (P1 chính) · §3 luồng 6 bước BGK tự thử · §4 Must M1–M7, Should S1/S2, Could, **Won't** · §5 cổng số (recall ≥ 0.90, FPR ≤ 0.10, p95 văn bản ≤ 6s / ảnh ≤ 12s, ≥ 10 người thật) · §6 câu hỏi BTC · §7 rủi ro R1–R6 |
| `.claude/skills/scam-analyzer/taxonomy.md` đã đối chiếu 25 kịch bản (hoặc ghi rõ chưa tìm được) | **FAIL** | `stat` → mtime **vẫn là `2026-11-24 18:09:21`** = giờ cài bộ kit, **không sửa lần nào trong ngày 1**. Dòng 5 vẫn nguyên văn bộ kit: "**Việc của ngày 1:** tìm thông báo gốc, đối chiếu và bổ sung đủ 25 mã kịch bản" → đây là việc còn treo, không phải kết luận "đã tìm, không ra". Đếm mã: G1=6, G2=4, G3=4, G4=5, G5=5 = **24 mã, thiếu 1**. `prompts/` vẫn không tồn tại → không có `prompts/analyzer_v0.md` (PLAN ngày 1, cột "Xong khi" của vai AI). |
| Repo, CI, tài khoản dịch vụ đã tạo; `.env.example` có đủ biến | **FAIL** (repo đã xong, CI + tài khoản chưa) | **Repo: PASS** — `git remote -v` → `origin https://github.com/linh080504/Momo_Challenge.git`; commit `1165717 chore: AI team kit + docs ngay 1`; `git status -sb` → `## main...origin/main` (đã đồng bộ); `git ls-remote --heads origin` → `refs/heads/main 1165717…`; 53 file được theo dõi. **CI: FAIL** — không có `.github/`; `find` toàn repo (trừ `.git`) **không thấy một file `*.yml`/`*.yaml`/`*.toml`/`package.json`/`requirements*.txt` nào** → chưa có workflow nào, và cũng chưa có project để CI build. **Tài khoản dịch vụ: FAIL** — không có bằng chứng ở bất kỳ đâu: `grep -i` trong `docs/` chỉ ra các dòng *kế hoạch* (PLAN/TASKS) về Vercel/Supabase/Safe Browsing, không có URL, không có dòng "đã lấy key", không có `apps/`, `infra/`. **`.env.example`: gần đủ** — 9 biến, phủ đúng 8 biến mà `.claude/skills/deploy-runbook/SKILL.md:19` yêu cầu + `ANALYZER_URL`; **thiếu `NEXT_PUBLIC_API_URL`** (chính runbook đó yêu cầu ở bước setup #2) và thiếu biến cho 2 tài khoản test của M6. |
| ≥ 50 mẫu dữ liệu đầu tiên (đã ẩn danh) trong `eval/` | **FAIL** | `eval/` chỉ có `dataset.example.jsonl` + `reports/`. **`eval/dataset.jsonl` không tồn tại.** Phân tích file mẫu: **18 dòng** (12 scam / 6 legit), `source: synthetic-example` 18/18, `synthetic: true` 18/18, **0 mẫu ảnh**, mtime `18:09:20` → đây là file mẫu của bộ kit, không phải dữ liệu đội thu. 18 < 50. Không có `eval/raw-notes/`, không có `eval/images/`. |

**Bằng chứng phụ (đã tự chạy lại):**
- `py -3 tests/test_kit_scripts.py` → **16/16 OK, exit 0**. Đúng như eval-qa báo.
- `eval/reports/20261124-184758-baseline.md` có thật: recall 0.917 · **FPR 0.167 (trượt cổng ≤ 0.10)** · p95 văn bản 0.001s (n=18) · **p95 ảnh n=0** · tự kết luận "CHƯA ĐẠT". Số này chạy trên 18 mẫu mẫu nên không dùng được làm số đo lần 1 của G1.
- **`eval/reports/latest.json` vẫn chưa tồn tại** → `/gate-check G2` (đọc `p95_text`/`p95_image` trong `latest.json`) hiện không có nguồn số. `run_eval.py` chỉ ghi `latest.json` khi đạt cổng và không chạy `--baseline`.
- `docs/DECISIONS.md` (mtime 19:47, 22 dòng quyết định) **không có dòng nào** cho phép dồn mốc "50 mẫu của G0" sang ngày 2 → F6 của lần kiểm trước vẫn mở.

**Việc phải làm cho từng FAIL (cập nhật từ lần 1)**

| # | Việc cụ thể | Người phụ trách | Xong khi |
|---|---|---|---|
| F1a | ~~`git init` + remote GitHub~~ ✅ **XONG** — `origin` + commit `1165717` đã đẩy lên `main` | backend-engineer / PM | — |
| F1b | Thêm `.github/workflows/ci.yml` chạy `python tests/test_kit_scripts.py` trên push/PR (bổ sung `pytest apps/api` khi có code); bật bảo vệ nhánh `main` + yêu cầu PR như `deploy-runbook` bước setup #1 | **backend-engineer** | Dán link 1 lần CI xanh vào STATUS |
| F1c | Tạo và xác nhận tài khoản dịch vụ (LLM + model dự phòng, Google Safe Browsing, Supabase region Singapore, Vercel, nền tảng API) → dán vào STATUS bằng chứng "key đã lấy được" (ví dụ: tên project + thời điểm tạo, **không dán giá trị key**) | **backend-engineer** | STATUS có 5 dòng xác nhận tài khoản |
| F2 | Taxonomy: tìm thông báo gốc 25 kịch bản (Công an TP Hà Nội 09/2026), bổ sung đủ 25 mã. **Nếu không truy được bản gốc: xóa dòng 5 và ghi thẳng** "đã tìm ngày 1 (liệt kê nguồn đã thử), không truy được bản gốc; 24 mã dưới đây do đội tổng hợp" | **ai-engineer** | `taxonomy.md` có mtime ngày 1 và một trong hai: đủ 25 mã, hoặc câu kết luận đã tìm không ra kèm nguồn |
| F3 | Viết `prompts/analyzer_v0.md` từ `.claude/skills/scam-analyzer/prompt-template.md`, nhúng taxonomy rút gọn (đầu vào của D2-AI-00/02) | **ai-engineer** | File tồn tại, chạy thử được với 1 mẫu |
| F4 | `eval/dataset.jsonl` ≥ 50 dòng hợp lệ theo `dataset-guide.md`, đã ẩn danh (`pii_mask.py` sạch), ghi chú gốc để ở `eval/raw-notes/`; **kèm ≥ 20 mẫu ảnh theo §5.1 brief** (có thể dồn sang mốc 100 mẫu nhưng phải ghi rõ) | **eval-qa** | `wc -l eval/dataset.jsonl` ≥ 50 + `run_eval.py --baseline` chạy được trên file đó |
| F5 | 3 màn tĩnh Next.js chạy local (`apps/web`) — PLAN ngày 1, `apps/` vẫn chưa tồn tại | **frontend-engineer** | `npm run dev` mở được 3 màn, ảnh chụp khổ 390px |
| F6 | **Vẫn mở:** nếu chấp nhận dồn mốc 50 mẫu của G0 sang `D2-QA-01` (70 mẫu, 25/11 17:00) thì ghi một dòng vào `docs/DECISIONS.md`; không im lặng bỏ qua | **pm-lead** | Có dòng DECISIONS hoặc F4 xong |
| F7 | `.env.example`: thêm `NEXT_PUBLIC_API_URL` (deploy-runbook setup #2) và biến cho 2 tài khoản test của M6; `TELEGRAM_BOT_TOKEN` đã xuống Could — ghi chú "chưa dùng vòng này" | **backend-engineer** | File có đủ biến khi dựng `apps/api`/`apps/web` |

**Chặn đường mới:** repo đã mở nên hợp đồng "commit stub `analyze()` trước 10:00 ngày 2" (`docs/TASKS.md` D2-AI-00) đã khả thi. Chặn đường còn lại là **F1c (tài khoản dịch vụ)** — không có key LLM thì mốc 14:00 ngày 2 "URL API staging" chỉ trả được stub, và **F4** — không có dữ liệu thật thì số đo lần 1 của G1 sẽ vẫn chạy trên mẫu tổng hợp.

## 2026-11-26 — MVP chạy local

- Next.js và FastAPI đã nối luồng kiểm tra chữ/ảnh, trả tiến trình và kết quả có bằng chứng. OCR tiếng Việt chạy cục bộ. Chế độ hạn chế hoạt động khi chưa có khóa dịch vụ.
- Hai vai user/ops, gửi báo cáo, gom chiến dịch theo thực thể, sửa nhóm, duyệt/bác bỏ, nhật ký và cảnh báo ở lần kiểm tra sau đã có trong mã. Đã có kiểm tra/tạo lại VietQR và chia sẻ tóm tắt 24 giờ.
- Kiểm thử local đạt 30 ca Python và một ca e2e trên trình duyệt. Ca e2e gửi ảnh PNG tổng hợp qua OCR, tạo link chia sẻ, báo cáo, duyệt và kiểm tra cảnh báo ở khổ 390px. Giao diện cũng đã được kiểm ở khổ 1280px. Next.js build và `docker compose config --quiet` đều thành công.
- Eval smoke local trên 23 mẫu tổng hợp, gồm 18 văn bản và 5 ảnh. Recall 1,00, báo nhầm 0,00, p95 văn bản 0,028 giây, p95 ảnh 0,62 giây, 0 lỗi API. Kết quả áp dụng cho tập kiểm tra kỹ thuật này.
- Bản public, model/Safe Browsing với khóa thật, PostgreSQL trên Supabase và eval chính thức vẫn cần xác minh. Báo cáo chất lượng vòng thi cần tập gán nhãn thật, holdout và kết quả thử với người dùng.

## 2026-11-27 — Bản nâng cấp chạy local

| Hạng mục | Bằng chứng hiện có | Việc tiếp theo |
|---|---|---|
| Cổng bảo mật, URL và QR | Kiểm thử chuẩn hóa IDN, nhận diện ký tự tương tự, QR liên kết, CRC VietQR và lọc dữ liệu trước khi gọi dịch vụ ngoài. RDAP `.com`/`.net` đã được kiểm thử bằng phản hồi mô phỏng. | Xác minh nguồn Safe Browsing và RDAP trên môi trường thử, rà quyền truy cập và giới hạn egress. |
| Qwen và biên lai | Qwen4-Max đã trả HTTP 200 qua QwenCloud Singapore. Một ca biên lai chạy Qwen thật, trả 8 vùng OCR và trạng thái giao dịch `unverified`. | Chạy eval chính thức, so sánh PaddleOCR/VLM, bổ sung bằng chứng bố cục và mẫu ảnh bị nén. |
| Ghi âm | Có form tải bản ghi, chuyển WAV mono 16 kHz và adapter Whisper cục bộ. Kiểm thử đã mô phỏng lệnh phiên âm. | Cài `whisper-cli` và trọng số, thử ghi âm thật đã xin phép, đo độ chính xác và độ trễ. |
| FraudURL và mô hình chuyên biệt | Huấn luyện, tạo manifest và nạp artifact FraudURL thành công trên dữ liệu tổng hợp. | Chuẩn bị dữ liệu đã xác minh để đánh giá và bật model. Các ứng viên FraudBERT, FraudDoc, FraudVoice và FraudFusion đang ở lộ trình. |
| Workspace và phản hồi | Playwright chạy qua báo cáo ảnh, mở đồ thị, chọn thực thể đã ẩn danh, duyệt và thấy cảnh báo ở lần kiểm tra lại. API phản hồi có kiểm tra vai trò và chỉ trả hồ sơ đã duyệt còn báo cáo. | Đo trên hồ sơ được phép dùng, hoàn thiện active learning, nâng đồ thị và tích hợp kênh cảnh báo được cấp quyền. |
| Kiểm thử và phát hành | 37 bài pytest đạt. Luồng Playwright chạy riêng thành công. Trình duyệt khổ 390px đã hiển thị vùng chữ trên ảnh biên lai và kiểm tra được QR liên kết. | Kiểm chứng staging/public, PostgreSQL/Supabase, eval chính thức và các phiên thử người dùng. |

Ưu tiên hiện tại là U-01 đến U-04 gồm dữ liệu, baseline, rà bảo mật và FraudURL. Kết quả thử local và dữ liệu tổng hợp được ghi theo phạm vi thử kỹ thuật. [Công việc nâng cấp](TASKS.md#công-việc-nâng-cấp-paypause-ai) · [Kịch bản nghiệm thu](USER_TESTS.md#kịch-bản-nghiệm-thu-bản-nâng-cấp)

Gói triển khai tiếp theo bắt đầu bằng hợp đồng sáu đầu vào và đo lại baseline. QA chuẩn bị hướng dẫn gán nhãn và tập URL song song để sẵn sàng cho đánh giá FraudURL. [Gói triển khai đầu tiên](TASKS.md#gói-triển-khai-đầu-tiên)

## Tiến độ thực hiện 15 bước

| Bước | Trạng thái | Bằng chứng hoặc việc chuyển tiếp |
|---|---|---|
| 1 · Hợp đồng và hai luồng sản phẩm | Hoàn thành | Có ma trận sáu đầu vào, quyền và lỗi ở Product Brief. OpenAPI mô tả NDJSON và hai dạng kết quả QR. Kiểm thử API đạt 23 ca. PostgreSQL chờ kiểm ở bước 2. |
| 2 · Môi trường và baseline | Hoàn thành trong phạm vi staging local | Compose chạy FE `3020`, API `8020` và PostgreSQL `55432` trên loopback, dùng volume riêng và migration `001_mvp.sql`. 41 bài kiểm thử đạt, gồm Playwright và PostgreSQL. Smoke Qwen4-Max `signals-v2` trên 23 mẫu tổng hợp đạt recall 1,00, báo nhầm 0,00, p95 văn bản 1,572 giây, p95 ảnh 2,159 giây và 0 lỗi. Staging từ xa và số đo chất lượng trên dữ liệu thật nằm ở mốc phát hành. |
| 3 · Cổng bảo mật | Hoàn thành luồng local | Cập nhật snapshot Public Suffix List, phân biệt tenant dùng chung, giới hạn tra cứu tới endpoint cố định và giữ đường dẫn riêng ngoài yêu cầu mạng. RDAP Verisign đã trả bằng chứng tuổi tên miền qua API. Safe Browsing qua test mô phỏng, khóa thật và chính sách mạng/lưu trữ môi trường đích chờ xác minh. |
| 4 · Dataset, tri thức và nội dung | Có bộ công cụ. Chờ dữ liệu đã duyệt | Eval gửi được sáu loại đầu vào và tách số mẫu, p95, lỗi theo loại. Có hướng dẫn gán nhãn và mẫu manifest. Tập tổng hợp dùng để chạy thử kỹ thuật. Tập đã xác minh và holdout cần bàn giao trước khi chốt chất lượng hoặc kích hoạt model ứng viên. |
| 5 · Sáu đầu vào và giao diện | Hoàn thành phần tích hợp local | Bật Whisper `base-q5_1` cho staging thử, API nhận WAV tiếng Việt tổng hợp và trả HTTP 200 trong 3,1 giây. Bộ kiểm thử cuối đạt 45 ca, gồm luồng trình duyệt ở 390px và 1280px, biên lai, QR liên kết, ghi âm và PostgreSQL. Whisper `large-v3-turbo-q5_0` đã chạy thử riêng. |
| 6–9 · Mô hình chuyên biệt, pháp y, RAG và đồ thị | Chờ benchmark chính thức | Cần tập train/holdout được duyệt theo từng tác vụ. Các thành phần local hiện có làm baseline. Chưa kích hoạt model huấn luyện từ dữ liệu smoke. |
| 10–13 · Workspace, cảnh báo và vòng học | Có luồng cơ bản. Còn phần mở rộng | Hồ sơ, quyền chuyên viên và cảnh báo sau duyệt đã qua staging local. Cần đo hiệu quả vận hành, gán nhãn cấp mẫu, thử registry và cấp quyền trước khi nối kênh cảnh báo hoặc nguồn giao dịch. |
| 14–15 · Pilot và phát hành | Chưa nghiệm thu | Cần kết quả eval holdout, các phiên thử với người dùng, hạ tầng phát hành và xác nhận quyền của các dịch vụ cần mở. |

### Phát hiện trong lượt smoke mở rộng

Với 29 mẫu tổng hợp đủ sáu đầu vào, API xử lý đủ lượt và recall đạt 1,00. FPR theo quy ước hiện tại là **33,3%** (4/12), vượt cổng 10%. Bốn mẫu hợp lệ trả `uncertain` gồm tên miền chính thức, VietQR, biên lai chưa xác minh và ghi âm. Giữ quy ước tính `uncertain` vào nhóm cảnh báo. Theo dõi thêm số ca `uncertain` theo kênh để bước 8–9 đánh giá lại định tuyến và hiệu chuẩn trên tập chính thức. [Hướng dẫn đánh giá](../eval/README.md#chuẩn-bị-dữ-liệu-sáu-đầu-vào)

Trên một câu tổng hợp tiếng Việt dài 3,5 giây, `base-q5_1` có WER 80% và `large-v3-turbo-q5_0` có WER 50%. Hai phép đo dùng 10 từ tham chiếu và xác nhận sự khác biệt trong một ca thử. Cần đo lại với ghi âm thật trước khi chọn model ASR. [Whisper cho staging](../infra/deploy/README.md#bật-nhận-dạng-ghi-âm-ở-staging)

[Kế hoạch xây dựng từng bước](PLAN.md#kế-hoạch-xây-dựng-từng-bước) · [Hợp đồng sáu đầu vào](PRODUCT_BRIEF.md#hợp-đồng-sáu-đầu-vào-và-hai-luồng-sản-phẩm)
