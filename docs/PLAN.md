# Kế hoạch 14 ngày — Trước Khi Chuyển

Đội 5 vai: **PM** (bạn), **AI**, **BE** (backend), **FE** (frontend), **QA** (dữ liệu + kiểm thử). Đội 4 người: PM kiêm QA phần phỏng vấn, AI kiêm gán nhãn.
Mỗi người mở Claude Code ở worktree riêng với agent của vai mình (xem README). Cổng: **G0 ngày 1 · G1 ngày 7 · G2 ngày 10 (feature freeze) · G3 ngày 13 (nộp)**. Không lùi hạn, chỉ cắt phạm vi.

Nhịp mỗi ngày: 9:00 standup 15 phút (`/daily-standup N`) · làm việc · demo nội bộ cuối ngày 3, 5, 7, 10 trên bản đã deploy · PM chốt STATUS trước 22:00.

---

## Ngày 0 (hôm nay, 1–2 giờ) — Cài bộ kit
- PM: làm theo README phần "Cài đặt", tạo repo, commit bộ kit, mời cả đội.
- Mọi người: cài Claude Code, `npx ctx7 setup --claude` (chọn "MCP server"), chạy `python3 tests/test_kit_scripts.py`.
- **Xong khi:** `claude mcp list` thấy context7 connected; gõ `@` trong ô chat thấy 7 agent; gõ `/` thấy các skill của dự án.

## Ngày 1 — Chốt đề → G0
| Vai | Việc | Agent / prompt mẫu | Xong khi |
|---|---|---|---|
| PM | Gửi câu hỏi BTC; hoàn thiện brief | `pm-lead`: "Phỏng vấn tôi bằng AskUserQuestion để hoàn thiện docs/PRODUCT_BRIEF.md" | Brief đủ 7 mục |
| AI | Tìm danh sách 25 kịch bản gốc của Công an TP Hà Nội; cập nhật taxonomy; chọn 2 LLM ứng viên; prompt v0 | `ai-engineer`: "Đọc skill scam-analyzer, viết prompts/analyzer_v0.md từ prompt-template.md, điền taxonomy rút gọn" | taxonomy.md có mã kịch bản; prompt v0 |
| BE | Monorepo, FastAPI `/health`, Supabase, CI, `.env.example` | `backend-engineer`: "Dựng apps/api FastAPI có /health trả version, pytest, Dockerfile; dùng context7 cho FastAPI" | CI xanh |
| FE | Next.js skeleton; phác 3 màn: nhập, kết quả, /ops | `frontend-engineer` | 3 màn tĩnh chạy local |
| QA | Thu 50 mẫu đầu (đã ẩn danh); cùng PM phỏng vấn 5–6 người | `eval-qa`: "Chuyển các mẫu trong eval/raw-notes thành eval/dataset.jsonl theo dataset-guide.md" | 50 dòng hợp lệ |
| QA | **[brief] `run_eval.py` gửi được ảnh** (`{text, image_base64, image_mime}`) + báo cáo tách `p95_text`/`p95_image` | | ✅ **XONG 2026-11-24** — 16 test pass |
| PM | **[brief] Mục 1 brief: số liệu có nguồn** | | ✅ xong 2026-11-24 |
| PM | **Sửa 4 chỗ lệch do đổi mốc p95** (gate-check, hook session-context, đường dẫn dataset-guide, ghi chú Windows) | | ✅ xong 2026-11-24 |
| PM | `/gate-check G0` lúc 21:00 | | **G0 ĐẠT** |

## Ngày 2 — Walking skeleton public
- BE: `POST /v1/analyze` gọi LLM với prompt v0, trả JSON theo schema; deploy API (giữ 1 instance); `/deploy-runbook smoke <URL>`.
- FE: trang nhập (dán chữ + tải ảnh) → thẻ kết quả đọc JSON; deploy Vercel.
- AI: bước 1–3 của pipeline (vision đọc ảnh, trích thực thể, ẩn danh bằng `pii_mask`).
- QA: 70 mẫu; chạy eval baseline (mốc "không có AI").
- **Xong khi:** dán ảnh chụp tin nhắn trên URL public → nhận kết quả trong < 10 giây.

## Ngày 3 — Bằng chứng + điểm lai · demo 1
- AI: tool tra bằng chứng (`domain_check`, Safe Browsing, danh sách đen), điểm lai theo `risk-scoring.md`, validate schema, hậu kiểm trích dẫn.
- BE: bảng `entities`, `reports`; `POST /v1/reports`; `POST /v1/qr/parse`.
- FE: thẻ kết quả đủ: mức nguy cơ, 3 dấu hiệu + trích dẫn, câu hỏi kiểm chứng, câu "do AI phân tích"; nút "Dùng mẫu".
- QA: 100 mẫu (≥ 20 ảnh); tách 20 mẫu sang `eval/holdout.jsonl` (tạo tay, hook chặn AI ghi file này).
- QA: **[brief] báo cáo eval tách p95 theo văn bản / ảnh** — `latest.json` có `p95_text` và `p95_image` riêng.
- **Xong khi:** demo 1 cho cả đội trên URL public.

## Ngày 4 — Chọn model bằng số đo
- AI + QA: chạy eval cho 2 LLM ứng viên → chọn model chính + dự phòng, ghi DECISIONS (kèm chi phí/độ trễ).
- BE: cache theo hash, rate limit, timeout, tự chuyển model dự phòng, trace Langfuse.
- FE: **[brief] màn chờ hiện tiến trình thật 3 chặng** (đã đọc ảnh → thực thể đã trích → đang tra bằng chứng); **KHÔNG hiện kết luận rủi ro sơ bộ rồi đổi sau**. Giao diện điện thoại, chữ ≥ 18px. Ảnh chụp 3 chặng ở khổ 390px.
- Security: "Dùng subagent security-reviewer rà apps/api: PII trong log, secret, phân quyền".
- **Xong khi:** báo cáo eval của model được chọn nằm trong `eval/reports/`.

## Ngày 5 — Sửa theo lỗi eval · demo 2
- AI: 2–3 vòng sửa prompt theo phân tích lỗi của QA (mỗi vòng một file prompt mới, chạy eval có `--compare`).
- BE: đăng nhập 2 vai (user, ops), 2 tài khoản test, seed dữ liệu demo.
- FE: bắt đầu `/ops`: hàng chờ báo cáo.
- QA: "thử như BGK" 10 đầu vào lạ → `eval/adversarial-<ngày>.md`.
- PM: `pitch-writer` viết khung slide + kịch bản video v0.
- **Xong khi:** recall tăng so với ngày 4, không tăng báo nhầm.

## Ngày 6 — Bàn làm việc vận hành (Future Workspace)
- AI: gom chiến dịch (trùng hash STK/SĐT/tên miền + độ giống kịch bản bằng embedding); AI viết hồ sơ chiến dịch và soạn cảnh báo công khai.
- BE: `GET /v1/ops/campaigns`, `POST /v1/ops/campaigns/{id}/decision`, nhật ký duyệt; duyệt → thực thể chuyển `approved`.
- FE: danh sách chiến dịch, trang chi tiết, nút Duyệt/Bác bỏ/Sửa.
- QA: test e2e: báo cáo → gom → duyệt → người dùng kế tiếp được cảnh báo.
- **Xong khi:** test e2e chạy xanh trên bản public.

## Ngày 7 — G1 · demo 3
- Cả đội: sửa lỗi tích hợp; mời 1 người ngoài đội thử không cần hướng dẫn; eval chính thức lần 1.
- PM: chốt 2 mục Should (mặc định: QR sạch, chế độ người thân); `/gate-check G1`.
- **Xong khi:** G1 ĐẠT. Chưa đạt → PM cắt phạm vi ngay trong tối nay.

## Ngày 8 — Should #1: VietQR
- BE: đọc ảnh QR (opencv), `POST /v1/qr/build`, so khớp người nhận trong QR với tin nhắn.
- FE: tải ảnh QR → hiện các trường đã giải mã; QR sạch chỉ khi rủi ro thấp + người dùng xác nhận người nhận.
- AI: thêm tín hiệu QR (CRC sai, người nhận lệch) vào điểm lai; thêm mẫu eval có QR.
- QA: thử với 5 người dùng thật, ghi `docs/USER_TESTS.md`.

## Ngày 9 — Should #2: Người thân
- BE: bot Telegram, liên kết người giám hộ bằng deep link, `POST /v1/guardian/notify`.
- FE: nút "Hỏi người thân", màn liên kết.
- AI: bản tóm tắt 2 câu cho người thân.
- QA: thêm 5 người dùng thật (tổng ≥ 10); xin phép quay phản ứng.
- PM: **[brief] phỏng vấn 1 người từng làm vận hành/CSKH** để xác nhận quy trình thủ công mô phỏng giống thực tế → biên bản trong `docs/USER_TESTS.md`.
- PM + pitch-writer: quay nháp video.

> Lưu ý Should #2 đã rút gọn (DECISIONS 2026-11-24): **không làm bot Telegram**. Thay bằng link chia sẻ chứa tóm tắt 2 câu, đã che STK/SĐT, hết hạn 24 giờ, người dùng tự gửi qua nút chia sẻ của hệ điều hành.

## Ngày 10 — G2 Feature freeze · demo 4
- AI: vòng tối ưu cuối, eval ĐẠT cổng.
- Rà soát song song (tùy chọn agent team, xem README): security-reviewer, eval-qa, pitch-writer cùng rà bản public.
- BE/FE: sửa mọi lỗi mức Cao trở lên.
- PM: `/gate-check G2`. **Từ tối nay chỉ sửa lỗi.**

## Ngày 11 — Ổn định + chốt số liệu
- BE: test tải 20 người cùng lúc, cảnh báo ngân sách LLM, giám sát uptime, nới rate limit cho tài khoản BGK.
- BE + AI: **[brief · chống rủi ro R1] chế độ hạn chế** — khi mọi LLM fail, trả kết quả dựa trên luật + danh sách đen, JSON đúng schema kèm cờ `degraded`, nói rõ "chế độ hạn chế". Xong khi: tắt key LLM → API vẫn trả JSON hợp lệ, không trả trang lỗi.
- QA + PM: **[brief] đo 5 chiến dịch thủ công vs `/ops`** (mỗi chiến dịch 8–10 báo cáo, 2 người khác nhau, đo cả thời gian lẫn số quyết định đúng) → bảng trong `docs/USER_TESTS.md`.
- QA: chạy holdout; chốt số cho slide từ `eval/reports/latest.json`.
- FE: sửa giao diện theo user test; chụp ảnh màn hình cho slide.
- PM: `/submission-pack slides`, `/submission-pack guide`, `/submission-pack readme` (bản 1).

## Ngày 12 — Đóng gói
- pitch-writer + PM: slide bản cuối, quay và dựng video, PDF 1 trang.
- BE: tạo zip mã nguồn sạch, quét secret.
- 20:00 dry run: một người ngoài đội làm theo PDF trên máy lạ, mạng 4G. `/submission-pack check`.

## Ngày 13 — Nộp → G3
- Sáng: sửa các FAIL của dry run; `/gate-check G3`.
- Trước 12:00: nộp 4 thành phần, chụp màn hình xác nhận. Lập lịch trực đến hết vòng chấm.

## Ngày 14 — Dự phòng + chuẩn bị chung kết
- `pitch-writer` soạn 15 câu hỏi khó và câu trả lời ≤ 40 giây (`submission/QA.md`); luyện thuyết trình 2 lần có bấm giờ.
- Hệ thống: chỉ hotfix có PM duyệt.

---

## Prompt mẫu theo vai

**PM (mở đầu ngày):** `/daily-standup 5` → "Dựa trên STATUS và PLAN, chia việc ngày mai thành task ≤ 1 ngày, mỗi task có chủ, file được sửa, tiêu chí xong."

**AI (sửa theo lỗi):** "Đọc báo cáo eval mới nhất. Nhóm các mẫu bỏ sót theo nguyên nhân. Đề xuất một thay đổi nhỏ nhất cho prompt hoặc luật, viết prompts/analyzer_vN.md, chạy eval có --compare, dán bảng chỉ số."

**BE (endpoint mới):** "Thêm POST /v1/ops/campaigns/{id}/decision theo hợp đồng trong agent backend-engineer. Viết test trước, chạy pytest, dán kết quả. Dùng context7 cho FastAPI và Supabase."

**FE (giao diện):** "Làm thẻ kết quả theo analysis.schema.json. Chụp màn hình bằng Playwright ở khổ 390px và 1280px, liệt kê khác biệt so với yêu cầu trong agent frontend-engineer rồi sửa."

**QA (phản biện):** "Dùng subagent eval-qa: tạo 10 đầu vào kiểu BGK chưa có trong eval, chạy qua API public, ghi eval/adversarial-<ngày>.md với kết quả và nhận xét."

**Rà soát độc lập trước merge:** "Dùng subagent security-reviewer rà diff của nhánh này so với main. Chỉ báo vấn đề ảnh hưởng an toàn hoặc yêu cầu."
