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


| Vai | Việc                                                                                                                | Agent / prompt mẫu                                                                                                  | Xong khi                              |
| --- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| PM  | Gửi câu hỏi BTC; hoàn thiện brief                                                                                   | `pm-lead`: "Phỏng vấn tôi bằng AskUserQuestion để hoàn thiện docs/PRODUCT\_BRIEF.md"                                | Brief đủ 7 mục                        |
| AI  | Tìm danh sách 25 kịch bản gốc của Công an TP Hà Nội; cập nhật taxonomy; chọn 2 LLM ứng viên; prompt v0              | `ai-engineer`: "Đọc skill scam-analyzer, viết prompts/analyzer\_v0.md từ prompt-template.md, điền taxonomy rút gọn" | taxonomy.md có mã kịch bản; prompt v0 |
| BE  | Monorepo, FastAPI `/health`, Supabase, CI, `.env.example`                                                           | `backend-engineer`: "Dựng apps/api FastAPI có /health trả version, pytest, Dockerfile; dùng context7 cho FastAPI"   | CI xanh                               |
| FE  | Next.js skeleton; phác 3 màn: nhập, kết quả, /ops                                                                   | `frontend-engineer`                                                                                                 | 3 màn tĩnh chạy local                 |
| QA  | Thu 50 mẫu đầu (đã ẩn danh); cùng PM phỏng vấn 5–6 người                                                            | `eval-qa`: "Chuyển các mẫu trong eval/raw-notes thành eval/dataset.jsonl theo dataset-guide.md"                     | 50 dòng hợp lệ                        |
| QA  | **\[brief\] `run_eval.py` gửi được ảnh** (`{text, image_base64, image_mime}`) + báo cáo tách `p95_text`/`p95_image` |                                                                                                                     | ✅ **XONG 2026-11-24** — 16 test pass  |
| PM  | **\[brief\] Mục 1 brief: số liệu có nguồn**                                                                         |                                                                                                                     | ✅ xong 2026-11-24                     |
| PM  | **Sửa 4 chỗ lệch do đổi mốc p95** (gate-check, hook session-context, đường dẫn dataset-guide, ghi chú Windows)      |                                                                                                                     | ✅ xong 2026-11-24                     |
| PM  | `/gate-check G0` lúc 21:00                                                                                          |                                                                                                                     | **G0 ĐẠT**                            |


## Ngày 2 — Walking skeleton public

- BE: `POST /v1/analyze` gọi LLM với prompt v0, trả JSON theo schema; deploy API (giữ 1 instance); `/deploy-runbook smoke <URL>`.
- FE: trang nhập (dán chữ + tải ảnh) → thẻ kết quả đọc JSON; deploy Vercel.
- AI: bước 1–3 của pipeline (vision đọc ảnh, trích thực thể, ẩn danh bằng `pii_mask`).
- QA: 70 mẫu; chạy eval baseline (mốc "không có AI").
- **Xong khi:** dán ảnh chụp tin nhắn trên URL public → nhận kết quả trong &lt; 10 giây.

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

- BE: phát hành link chia sẻ tóm tắt đã che STK/SĐT và hết hạn sau 24 giờ.
- FE: nút "Hỏi người thân", trang mở link và chia sẻ qua chức năng hệ điều hành.
- AI: mẫu tóm tắt 2 câu cho từng mức rủi ro.
- QA: thêm 5 người dùng thật (tổng ≥ 10); xin phép quay phản ứng.
- PM: **[brief] phỏng vấn 1 người từng làm vận hành/CSKH** để xác nhận quy trình thủ công mô phỏng giống thực tế → biên bản trong `docs/USER_TESTS.md`.
- PM + pitch-writer: quay nháp video.

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

## Kế hoạch bổ sung từ kiến trúc hệ thống

Các mốc dưới đây bám theo kế hoạch 14 ngày và phạm vi đã chốt trong [Product Brief](PRODUCT_BRIEF.md#4-phạm-vi).


| Mốc                                              | Chủ trì           | Việc triển khai                                                                                                                                                                                                                                                                                                                                                                       | Xong khi                                                                                                                                                 |
| ------------------------------------------------ | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ngày 2 · Đầu vào và trích xuất                   | FE · BE · AI      | Nhận tin nhắn dán từ SMS, Zalo, mạng xã hội, ảnh chụp và URL theo hợp đồng `/v1/analyze`. Chuẩn hóa đầu vào, đọc chữ trong ảnh, trích số tài khoản, số điện thoại và tên miền. Che dữ liệu cá nhân trước khi gửi sang dịch vụ ngoài và dùng văn bản nguồn để đối chiếu trích dẫn trong lúc xử lý.                                                                                     | Ảnh chụp và văn bản đi qua cùng luồng phân tích sau bước đọc ảnh. Ảnh lỗi trả thông báo rõ ràng.                                                         |
| Ngày 3 · Nguồn dữ liệu và điểm rủi ro            | AI · BE           | Tra mẫu lừa đảo đã biết, tên miền thương hiệu chính thức, Google Safe Browsing và danh sách thực thể đã duyệt. Kết hợp luật với LLM để chấm điểm 0–100 từ các tín hiệu như giả mạo thương hiệu, link nguy hiểm, yêu cầu chuyển tiền, thông tin bất thường và mẫu lừa đảo đã biết.                                                                                                     | Kết quả có mức nguy cơ, dấu hiệu kèm trích dẫn, câu hỏi kiểm chứng và hành động gợi ý.                                                                   |
| Ngày 4 · Chọn cách đọc ảnh                       | AI · QA           | Đo độ chính xác đọc ảnh tiếng Việt và độ trễ. Nếu các model ứng viên đọc ảnh chưa đạt, thử OCR riêng như PaddleOCR để lấy chữ và tọa độ, ưu tiên ảnh có bố cục phức tạp. Nhận diện ngôn ngữ và dùng VLM để hiểu logo hoặc giao diện giả mạo là các hướng thử thêm khi dữ liệu eval cho thấy cần.                                                                                      | Có báo cáo so sánh trên ảnh thật đã ẩn danh, nêu lỗi trích xuất và ảnh hưởng tới recall, tỷ lệ báo nhầm, p95.                                            |
| Ngày 5–7 · Bàn làm việc vận hành và cảnh báo web | AI · BE · FE · QA | `/ops` tiếp nhận báo cáo, hiển thị bằng chứng và gom chiến dịch theo thực thể hoặc mẫu tương tự. Trang chi tiết hiển thị mức nguy cơ, số báo cáo liên quan và các biến thể link. Chuyên viên duyệt hoặc bác bỏ, hệ thống ghi người duyệt và thời điểm. Kết quả phân tích hiển thị ngay sau khi xử lý. Cảnh báo đã xác nhận xuất hiện trên web ở lần kiểm tra liên quan sau khi duyệt. | Test e2e đi từ gửi báo cáo đến gom chiến dịch, duyệt và thấy cảnh báo khi kiểm tra lại. Người dùng tự quyết định dừng và xác minh trước khi chuyển tiền. |
| Ngày 8 · VietQR (Should #1)                      | BE · AI · FE      | Giải mã ảnh QR để lấy ngân hàng, số tài khoản, số tiền và nội dung. Kiểm tra CRC và đối chiếu người nhận với tin nhắn.                                                                                                                                                                                                                                                                | Hiển thị thông tin giải mã và đưa kết quả đối chiếu vào phân tích. Chỉ tạo QR sạch khi rủi ro thấp và người dùng xác nhận người nhận.                    |


### Hạng mục mở rộng

- **Model ứng viên.** Sơ đồ gợi ý Qwen3-VL và LLaVA cho phân tích hình ảnh, Qwen3 và Llama cho suy luận văn bản. Việc chọn model dựa trên số đo eval ngày 4.
- **Ghi âm (Could).** Thử ASR như Whisper để chép lời cuộc gọi rồi đưa bản chép lời qua luồng ẩn danh và phân tích văn bản.
- **Bảng tổng quan `/ops` (Could).** Bổ sung số báo cáo trong 24 giờ, xu hướng và phân bố chiến dịch theo mức nguy cơ dựa trên dữ liệu đo được.
- **Cảnh báo đa kênh (lộ trình).** Mở rộng cảnh báo đã duyệt từ web sang email, SMS và thông báo nội bộ cho chuyên viên hoặc CSKH.

---

## Lộ trình nâng cấp PayPause AI

Cập nhật 2026-11-27. Kế hoạch 14 ngày ở trên là mốc MVP của vòng thi. Lộ trình này bắt đầu từ bản local đã kiểm thử và ưu tiên chất lượng dữ liệu, đánh giá từng năng lực rồi mới phát hành. [Trạng thái hiện tại](STATUS.md#2026-11-27--bản-nâng-cấp-chạy-local) · [Danh sách công việc](TASKS.md#công-việc-nâng-cấp-paypause-ai)

Luồng mục tiêu đi từ **tin nhắn, hình ảnh, URL, QR, ghi âm và biên lai** qua sáu tầng. Tín hiệu hỗ trợ người dùng xác minh trước khi chuyển tiền. Quyết định đã được chuyên viên xác nhận có thể quay lại hệ thống qua vòng phản hồi có kiểm duyệt.

| Tầng | Nền hiện có | Việc cần làm và tiêu chí nghiệm thu |
|---|---|---|
| **1. Deterministic Security & Trust Gateway** | Kiểm tra định dạng, giới hạn dữ liệu, IDN/Punycode, ký tự tương tự, tên miền thương hiệu, QR liên kết và CRC VietQR. Đối chiếu thực thể HMAC với chiến dịch đã duyệt. Có Safe Browsing và RDAP `.com`/`.net` theo cấu hình. | Rà danh mục tên miền chính thức, mở rộng độ phủ typosquatting, RDAP và nguồn threat intelligence đã được cấp quyền. Kiểm tra quyền truy cập, mã hóa dữ liệu lưu trữ, giới hạn egress và giám sát. Kiểm thử cổng ứng dụng với dữ liệu nhập bất thường và nội dung chèn chỉ dẫn, xác nhận nhà cung cấp chỉ nhận dữ liệu đã định tuyến và đích kết nối luôn là dịch vụ được cấu hình. |
| **2. Specialized Fine-tuned AI Models** | Đã so sánh FraudURL LightGBM và XGBoost trên tập UCI. Giữ kết quả làm benchmark tham chiếu. | **FraudBERT-VN** dùng PhoBERT đa nhiệm với ba đầu ra nhãn lừa đảo, thủ đoạn và vùng bằng chứng, rồi so sánh ONNX INT8 với bản gốc. **FraudDoc-VN** đánh giá DTD/DocTamper, OpenCV và OCR. **FraudVoice-VN** benchmark AASIST/XLS-R trên tiếng Việt. **FraudFusion-ML** học từ các nhóm tín hiệu và đánh giá xác suất đã hiệu chuẩn. Mỗi ứng viên có phiên bản, dữ liệu được phép dùng và kết quả holdout. URL trong MVP dùng cổng bảo mật và nguồn bằng chứng ở tầng 1. |
| **3. Deep Multimodal Reasoning** | Có Fast Path theo luật và bằng chứng đã xác minh. Deep Path dùng Qwen4-Max, OCR hiện tại và tri thức truy xuất theo nhóm thủ đoạn. Nhánh ghi âm đã có adapter Whisper cục bộ. | Benchmark PP-OCRv5, PP-OCRv6 và PaddleOCR-VL trên ảnh tiếng Việt. Đánh giá Whisper `large-v3-turbo` trên giọng vùng miền và bản ghi nhiễu. Thử Qwen3-VL-8B và Gemini 2.5 Flash theo quyền sử dụng dữ liệu. Huấn luyện ứng viên FraudLLM Qwen3-8B + QLoRA, xây Vietnam Scam RAG với BGE-M3 và BGE-reranker-v2-m3. Mở rộng router theo loại dữ liệu, độ phức tạp và độ tin cậy. Đo chất lượng, chi phí, tỷ lệ gọi Deep Path và p95 theo từng loại đầu vào. |
| **4. Graph Intelligence & Adaptive Risk** | Có nhóm chiến dịch theo thực thể ẩn danh, đồ thị cùng báo cáo và liên kết giữa chiến dịch. Điểm hiện tại dùng luật, bằng chứng và kết quả model khả dụng. | Thêm liên kết ảnh tương tự, mẫu nội dung, QR và người nhận có căn cứ truy xuất. Lưu nguồn, thời điểm và độ tin cậy của cạnh. Đo tỷ lệ gộp nhầm và tách nhầm chiến dịch. Kết hợp bằng chứng độc lập, giảm trùng tín hiệu và kiểm tra hiệu chuẩn với FraudFusion. |
| **5. Human-Centered Action & Fraud Ops** | Có khuyến nghị tạm dừng, đối chiếu người nhận, LangGraph trong `/ops`, bản nháp và cảnh báo web sau duyệt. | Nâng hàng đợi điều tra, bổ sung thời gian xử lý và xu hướng 24 giờ, định nghĩa kịch bản review và quyền theo vai trò. Thử cảnh báo in-app, email/SMS và nội bộ sau khi có quyền, nhật ký và cơ chế chống gửi trùng. Đối chiếu giao dịch chỉ khi có nguồn thanh toán được cấp quyền. |
| **6. Continuous Learning & AI Governance** | `/v1/ops/feedback` cung cấp tín hiệu đã ẩn danh của hồ sơ đã duyệt. FraudURL có manifest, checksum và chỉ số holdout. | Xây hàng đợi active learning cho ca mơ hồ và mẫu bị bỏ sót. Gán nhãn đúng đơn vị mẫu, ghi nguồn và quyền sử dụng, kiểm tra rò rỉ giữa tập train/holdout. Lưu dataset, model, prompt, cấu hình và báo cáo eval theo phiên bản. Chuyên viên duyệt ứng viên trước thử nghiệm, theo dõi sai lệch và chuẩn bị phiên bản quay lui. |

### Năm nhóm bằng chứng pháp y biên lai

1. **Vật lý.** Đọc metadata và đo sai khác khi nén lại JPEG. So sánh với ảnh nguyên bản và ảnh qua ứng dụng nhắn tin.
2. **Thị giác.** Dùng vùng OCR để kiểm tra bố cục, hình học, khoảng cách và đặc điểm chữ theo mẫu được xác minh.
3. **Học sâu.** Đánh giá bản đồ vùng nghi chỉnh sửa từ DTD trên dữ liệu có nhãn vị trí sửa.
4. **Ngữ nghĩa.** Đối chiếu các trường số tiền, thời gian, trạng thái và mã giao dịch từ OCR/VLM, kèm bằng chứng cụ thể cho các trường mâu thuẫn.
5. **Giao dịch.** Đối chiếu qua nguồn ngân hàng hoặc đối tác đã cấp quyền. Giữ trạng thái `unverified` khi chỉ có ảnh. Kết quả hiển thị ảnh gốc, vùng chữ, vùng cần xem lại và diễn giải theo nguồn.

### Multi-Agent AI Workspace

Supervisor giới hạn quyền và điều phối sáu tác nhân trong LangGraph. **Detection** tổng hợp tín hiệu rủi ro. **Threat Intel** đối chiếu nguồn đã xác minh. **Forensics** trình bày bằng chứng ảnh và ghi âm. **Investigation** nối thực thể và chiến dịch. **Protection** đề xuất bước xác minh cho người dùng. **Report** soạn hồ sơ và bản nháp cảnh báo.

Human Approval Gateway kiểm tra vai trò chuyên viên, phiên bản hồ sơ và quyết định duyệt hoặc bác bỏ. Quyền cập nhật cảnh báo nằm ở API vận hành. Quyết định chặn tài khoản hoặc thực hiện giao dịch thuộc hệ thống có thẩm quyền của đối tác.

### Thứ tự triển khai

1. **Chốt baseline và dữ liệu.** Chuẩn bị mẫu tiếng Việt đã ẩn danh và được phép sử dụng, khóa holdout, đo baseline local và staging theo loại đầu vào.
2. **Kiểm thử các thành phần đã có.** Chạy Whisper thật, kiểm thử cổng URL, OCR biên lai và fallback. Ghi lại cấu hình, số đo, lỗi và hạn mức.
3. **Benchmark và thử mô hình ứng viên.** Xây tập nhãn theo tác vụ, chạy so sánh mô hình chuyên biệt, OCR/VLM, FraudLLM và RAG ở môi trường thử. Giữ bộ luật và bằng chứng xác minh làm nền khi phụ thuộc ngoài gián đoạn.
4. **Kiểm chứng vận hành và phát hành.** Đo quy trình có chuyên viên, kiểm thử quyền và việc phát cảnh báo sau duyệt. Mở kênh tích hợp khi có quyền và có thể quay lui. Đo lại sau mỗi thay đổi model hoặc nguồn dữ liệu.

### Kế hoạch xây dựng từng bước

Bắt đầu từ bản PayPause AI đã chạy local. Mỗi bước có gói bàn giao để đội chạy thử và kiểm tra. Mở môi trường thử sau khi chốt baseline, mở pilot sau khi nghiệm thu quyền và chất lượng, mở các tích hợp thật theo quyền và ngân sách đã xác nhận.

| Mốc | Bước | Bản chạy được khi kết thúc mốc |
|---|---|---|
| 1 · Nền tảng và luồng chính | 1–5 | Web và API staging có luồng kiểm tra, hồ sơ dữ liệu mẫu, nguồn bằng chứng và trải nghiệm lỗi rõ ràng. |
| 2 · AI và kiểm định đa phương thức | 6–9 | Có báo cáo so sánh các ứng viên, cơ chế chọn Fast/Deep Path, kết quả biên lai có vùng đối chiếu và hồ sơ chiến dịch truy xuất được bằng chứng. |
| 3 · Vận hành có chuyên viên | 10–13 | Có bàn điều tra, luồng duyệt và phát cảnh báo kiểm thử, phản hồi có kiểm duyệt và quy trình chọn phiên bản mô hình. |
| 4 · Pilot và vận hành | 14–15 | Có kết quả thử nghiệm, hồ sơ phát hành, giám sát, phương án quay lui và tài liệu bàn giao. |

#### Bước 1. Chốt luồng sản phẩm và hợp đồng dữ liệu

- **Làm:** Vẽ hai hành trình từ điểm bắt đầu đến hành động cuối. Người dùng chọn đầu vào, xem tiến trình, nhận bằng chứng, xác minh, báo cáo hoặc hỏi người thân. Chuyên viên tiếp nhận, điều tra, kiểm tra bản nháp, duyệt hoặc bác bỏ. Chốt cấu trúc request, response, tiến trình và mã lỗi cho `/v1/analyze`, `/v1/analyze/stream` và `/v1/qr/parse`.
- **Bàn giao:** Sơ đồ hai hành trình, ma trận vai trò và bảng liên hệ kênh đầu vào với màn hình, endpoint, giới hạn và trạng thái.
- **Qua bước khi:** FE, BE và QA thử được cùng ví dụ hợp lệ, ca thiếu dữ liệu và ca lỗi cho từng luồng. [Phạm vi sản phẩm](PRODUCT_BRIEF.md#phạm-vi-phiên-bản-nâng-cấp-paypause-ai)

#### Bước 2. Dựng môi trường và đo baseline

- **Làm:** Chạy FE, API, OCR/QR, Qwen, SQLite local và PostgreSQL staging. Chuẩn hóa secret, hai vai demo, migration và CI theo cấu trúc repo. Ghi phiên bản mã, prompt, nguồn bằng chứng và cấu hình của lượt đo. Đo độ trễ và kết quả trên bộ smoke cố định.
- **Bàn giao:** Runbook khởi động, bản staging, báo cáo baseline theo loại đầu vào, log smoke đã che thông tin.
- **Qua bước khi:** Chạy lại được text, ảnh, QR, chia sẻ và duyệt hồ sơ từ môi trường sạch. Khi Qwen gián đoạn, API vẫn trả đúng schema với chế độ hạn chế ở các ca có thể tiếp tục. [Cấu hình và dịch vụ](ACCOUNTS.md#cấu-hình-và-dịch-vụ-cho-bản-nâng-cấp)

#### Bước 3. Hoàn thiện cổng bảo mật và nguồn bằng chứng

- **Làm:** Rà giới hạn dữ liệu và định dạng theo từng kênh. Chuẩn hóa IDN/Punycode, đối chiếu tên miền thương hiệu, đánh giá homoglyph và typosquatting. Kiểm tra QR liên kết, CRC VietQR và người nhận đã xác minh. Mở Safe Browsing và RDAP theo quyền, hạn mức và độ phủ. Ràng buộc kết nối đi ra, phạm vi dữ liệu đưa vào LLM, quyền truy cập và dữ liệu lưu trữ.
- **Bàn giao:** Danh mục nguồn có chủ sở hữu, quy tắc tra cứu và ma trận phân quyền. Báo cáo kiểm thử bảo mật ứng dụng và tình huống nguồn tra cứu vắng mặt.
- **Qua bước khi:** Xác nhận URL do người dùng cung cấp được phân tích cục bộ, nhà cung cấp chỉ nhận dữ liệu đúng phạm vi, báo cáo chờ duyệt không trở thành cảnh báo khi đối chiếu người nhận.

#### Bước 4. Xây dataset, tri thức và nội dung tiếng Việt

- **Làm:** Thu thập mẫu có quyền sử dụng và tạo mẫu tổng hợp có ghi nguồn. Gán nhãn theo thủ đoạn, mức độ, vùng bằng chứng, loại đầu vào và đơn vị thích hợp. Chuẩn bị cả mẫu sạch và ca khó dễ báo nhầm. Tách train/dev/holdout theo chiến dịch, tên miền, người nói hoặc mẫu biên lai để cách ly dữ liệu liên quan.
- **Bàn giao:** Manifest, hướng dẫn gán nhãn, dữ liệu đã che, bộ thẻ tri thức có nguồn và bộ nội dung giao diện đã được duyệt. Ghi mẫu nào là tổng hợp và mẫu nào có người xác minh.
- **Qua bước khi:** QA có thể lấy một kết quả bất kỳ và truy lại nguồn, nhãn, phiên bản, tập dữ liệu và quyền sử dụng. Holdout được khóa trước khi chọn model. [Nội dung cần chuẩn bị](#nội-dung-cần-chuẩn-bị)

#### Bước 5. Nối sáu kênh đầu vào và giao diện người dùng

- **Làm:** Hoàn chỉnh màn nhập và kết quả tone hồng trên điện thoại và máy tính. Tin nhắn/URL đi qua chuẩn hóa và trích thực thể. Ảnh chụp dùng OCR. QR đọc loại và cấu trúc. Ghi âm chuyển WAV mono 16 kHz rồi chạy thử Whisper với trọng số cục bộ. Biên lai giữ ảnh gốc trong giới hạn để hiển thị vùng OCR và dấu hiệu ảnh. Hoàn thiện lỗi, tiến trình, chia sẻ, báo cáo và câu hỏi kiểm chứng.
- **Bàn giao:** Sáu luồng có kịch bản mẫu, trạng thái lỗi và hợp đồng FE–BE. Phiên âm thật hoặc tình trạng chưa cấu hình được ghi rõ trong báo cáo chạy thử.
- **Qua bước khi:** QA thực hiện trọn luồng ở 390px và 1280px, nhận đúng tiến trình và thấy một kết quả cuối. Tệp thiếu bộ xử lý có chỉ dẫn rõ để người dùng tiếp tục.

#### Bước 6. Huấn luyện và đánh giá mô hình chuyên biệt

- **Làm:** Tạo FraudBERT-VN đa nhiệm, đo trước và sau khi xuất ONNX INT8. Thử DTD/DocTamper kết hợp OCR/OpenCV cho FraudDoc-VN, AASIST/XLS-R cho FraudVoice-VN. Dùng cùng split khi so sánh phiên bản của một tác vụ. Benchmark FraudURL đã lưu để tham chiếu. Đánh giá chất lượng kiểm tra URL của MVP theo U-04.
- **Bàn giao:** Dataset phiên bản, model artifact và manifest có checksum, kết quả holdout, tài nguyên chạy và tiêu chí kích hoạt cho từng ứng viên.
- **Qua bước khi:** Mỗi ứng viên có đánh giá recall, báo nhầm và độ trễ theo tác vụ. Chọn artifact theo tiêu chí đã chốt hoặc ghi lý do giữ bộ phân tích hiện tại. FraudFusion được đánh giá ở bước 9 khi các nguồn tín hiệu đã sẵn sàng.

#### Bước 7. Kiểm định biên lai và dữ liệu nghe nhìn

- **Làm:** Benchmark OCR hiện tại cùng PP-OCRv5, PP-OCRv6 và PaddleOCR-VL trên ảnh tiếng Việt. Đo Whisper `large-v3-turbo` theo giọng vùng miền và độ nhiễu. Với biên lai, triển khai các kiểm tra vật lý, thị giác, học sâu và ngữ nghĩa. Đối chiếu giao dịch qua nguồn được cấp quyền ở bước 11.
- **Bàn giao:** Bảng chất lượng OCR/ASR, báo cáo vùng bằng chứng và thẻ biên lai hiển thị ảnh gốc cùng trạng thái xác minh. Có bộ ảnh nguyên bản, ảnh qua nén và ảnh có nhãn vùng thay đổi để đánh giá.
- **Qua bước khi:** QA xác định được bằng chứng nào đến từ OCR, nén ảnh hoặc model. Người dùng hiểu trạng thái `unverified` khi ứng dụng mới có ảnh. [Năm nhóm bằng chứng biên lai](#năm-nhóm-bằng-chứng-pháp-y-biên-lai)

#### Bước 8. Xây định tuyến, suy luận sâu và Vietnam Scam RAG

- **Làm:** Chốt điều kiện vào Fast Path theo bằng chứng và độ tin cậy, hoặc Deep Path theo loại đầu vào và độ phức tạp. Đánh giá Qwen4-Max, ứng viên Qwen3-8B + QLoRA, Qwen3-VL-8B và Gemini 2.5 Flash theo phạm vi dữ liệu được phép gửi. Thử BGE-M3 và reranker trên kho tri thức đã duyệt. Giới hạn ngân sách, độ trễ và kiểm tra kết quả theo schema.
- **Bàn giao:** Bảng định tuyến, bộ nguồn truy xuất kèm phiên bản, báo cáo chất lượng và lựa chọn model chính/dự phòng cho từng loại đầu vào.
- **Qua bước khi:** Có ca truy xuất đúng nguồn, ca thiếu bằng chứng và ca nhà cung cấp lỗi. Đo được tỷ lệ gọi Deep Path, chi phí mỗi ca, p95 và độ chính xác so với baseline.

#### Bước 9. Nâng đồ thị chiến dịch và tổng hợp rủi ro

- **Làm:** Định nghĩa nút báo cáo, chiến dịch, tên miền, thông tin người nhận đã che, QR và dấu hiệu ảnh tương tự. Gắn nguồn, thời điểm và độ tin cậy cho cạnh. Kiểm tra gộp và tách chiến dịch. Huấn luyện ứng viên FraudFusion trên tín hiệu độc lập, so sánh điểm đã hiệu chuẩn với baseline và xử lý trường hợp thiếu nguồn.
- **Bàn giao:** Hợp đồng dữ liệu đồ thị, API truy xuất, bộ ca gộp/tách và báo cáo hiệu chuẩn rủi ro.
- **Qua bước khi:** Chuyên viên xem được lý do hai báo cáo liên quan. QA đo được tỷ lệ gộp nhầm, tách nhầm và ảnh hưởng của từng nguồn khi bị thiếu.

#### Bước 10. Hoàn thiện Multi-Agent Workspace và duyệt hồ sơ

- **Làm:** Nâng Supervisor và sáu tác nhân trong LangGraph. Detection tổng hợp tín hiệu, Threat Intel trình bày nguồn đã xác minh, Forensics hiển thị bằng chứng media, Investigation mở đồ thị, Protection đề xuất hành động và Report soạn bản nháp. Hoàn thiện hàng đợi, bộ lọc, tổng quan 24 giờ và lịch sử quyết định. Kiểm tra vai trò và phiên bản hồ sơ khi duyệt.
- **Bàn giao:** Luồng `/ops` từ báo cáo đến quyết định, bản nháp có nguồn, dữ liệu đồ thị và nhật ký thay đổi. Chuyên viên có thể đối chiếu lại bằng chứng trước khi duyệt.
- **Qua bước khi:** Hai vai demo chạy được kịch bản báo cáo, duyệt, bác bỏ, báo cáo cập nhật đồng thời và người dùng thấy cảnh báo sau duyệt. [Vai trò tác nhân](#multi-agent-ai-workspace)

#### Bước 11. Tích hợp cảnh báo và đối chiếu giao dịch

- **Làm:** Kiểm chứng cảnh báo web trước. Thử in-app, email/SMS và thông báo nội bộ trong môi trường thử được cấp quyền. Kiểm tra chống gửi trùng, ghi kết quả gửi và thử lại khi dịch vụ lỗi. Khi có nguồn giao dịch được cấp quyền, kiểm tra danh tính giao dịch, độ mới của dữ liệu và điều kiện cập nhật trạng thái.
- **Bàn giao:** Mẫu nội dung theo kênh, trạng thái gửi, nhật ký phê duyệt và kết quả kiểm thử tích hợp. Ghi riêng các kênh sẵn sàng chạy thật và các kênh còn chờ đối tác.
- **Qua bước khi:** Cảnh báo được phát theo đúng quyết định đã duyệt. Trạng thái giao dịch ghi rõ nguồn xác minh, hoặc tiếp tục là `unverified` khi chưa đủ bằng chứng.

#### Bước 12. Tổ chức phản hồi và hàng đợi gán nhãn

- **Làm:** Dùng `/v1/ops/feedback` lấy tín hiệu cấp chiến dịch. Chọn ca mơ hồ, bỏ sót hoặc báo nhầm để chuyên viên xem lại. Gắn lại nhãn ở cấp URL, văn bản, đoạn ghi âm hoặc vùng ảnh khi dùng cho model tương ứng. Kiểm tra quyền dữ liệu và phân tách tập trước khi dùng mẫu đã xác minh.
- **Bàn giao:** Hàng đợi gán nhãn, lịch sử quyết định nhãn, phiên bản dataset và báo cáo số mẫu theo nguồn. Ghi cách xử lý mẫu bị rút hoặc chỉnh nhãn.
- **Qua bước khi:** QA theo được mẫu từ hồ sơ đến bản dataset và biết mẫu có đủ điều kiện huấn luyện hay cần xác minh thêm.

#### Bước 13. Quản lý model và thử nghiệm phát hành

- **Làm:** Lưu phiên bản model, prompt, cấu hình router, dataset và báo cáo eval. Chuẩn hóa phê duyệt ứng viên, kiểm tra checksum, triển khai thử và quay lui. Theo dõi chi phí, lỗi provider và biến động tỷ lệ lớp theo phiên bản.
- **Bàn giao:** Model registry, báo cáo so sánh ứng viên với bản đang dùng và hướng dẫn đổi phiên bản. Ghi rõ model nào đã thử trên dữ liệu tổng hợp và model nào đã qua holdout thật.
- **Qua bước khi:** Đội thử được một lượt đưa ứng viên lên staging, nhận biết chỉ số xuống và quay lui về phiên bản đã duyệt.

#### Bước 14. Nghiệm thu sản phẩm và chạy pilot

- **Làm:** Chạy eval chính thức theo Product Brief, thêm số đo OCR, ASR, biên lai, đồ thị và định tuyến. Kiểm thử phân quyền, tải và tình huống provider lỗi. Mời ít nhất 10 người thử. Đo 5 chiến dịch, mỗi chiến dịch 8–10 báo cáo, so sánh thao tác thủ công và `/ops` trên thời gian lẫn quyết định đúng.
- **Bàn giao:** Báo cáo holdout, kết quả thử người dùng, bảng lỗi còn mở, gói demo và biên bản chốt phạm vi pilot.
- **Qua bước khi:** Có bằng chứng cho recall, báo nhầm, p95 và quyền vận hành. PM ghi quyết định phát hành theo các mốc trong brief và liệt kê các năng lực có thể giới thiệu dựa trên số đo. [Chỉ số thành công](PRODUCT_BRIEF.md#5-chỉ-số-thành-công) · [Kịch bản nghiệm thu](USER_TESTS.md#kịch-bản-nghiệm-thu-bản-nâng-cấp)

#### Bước 15. Triển khai, giám sát và bàn giao

- **Làm:** Phát hành phiên bản đã duyệt, kiểm tra health, đăng nhập, phân tích, duyệt và cảnh báo trên môi trường đích. Theo dõi tỷ lệ lỗi, p95, trạng thái hàng đợi, hạn mức dịch vụ và kết quả giao cảnh báo. Thiết lập người xử lý sự cố, quy trình luân chuyển key, sao lưu/phục hồi và quay lui.
- **Bàn giao:** URL phát hành, phiên bản và cấu hình đã duyệt, runbook vận hành, báo cáo pilot, bằng chứng kiểm tra sau khi triển khai.
- **Qua bước khi:** Người trực có thể xử lý nguồn ngoài bị lỗi, chuyển về cấu hình ổn định và xác nhận phân tích cùng luồng duyệt tiếp tục hoạt động.

### Nội dung cần chuẩn bị

| Nội dung | Gói nội dung | Người duyệt và cách kiểm tra |
|---|---|---|
| Website và trợ lý | Trang chủ tone hồng, hướng dẫn sáu đầu vào, mẫu dùng thử, tiến trình thật, cảnh báo lỗi và lời nhắc xác minh. Chatbox dùng cùng dịch vụ phân tích và hướng người dùng đến màn hình phù hợp khi cần tải tệp. | FE + PM. Thử khổ 390px và 1280px, kiểm tra câu chữ đúng năng lực đang bật. |
| Kết quả rủi ro | Câu tóm tắt cho 4 mức, trích dẫn và vùng bằng chứng, nguồn, câu hỏi kiểm chứng, hành động gợi ý, trạng thái hạn chế và trạng thái giao dịch chưa xác minh. | QA + chuyên viên. Đối chiếu từng nhận định với đầu vào và nguồn. |
| Kho tri thức và dataset | Năm nhóm thủ đoạn G1–G5, biến thể theo thời điểm như Black Friday, mẫu sạch, ví dụ nhạy cảm đã che, hướng dẫn kiểm chứng, dữ liệu kiểm thử theo sáu đầu vào. | QA + người gán nhãn. Mỗi thẻ tri thức có nguồn, ngày rà, phiên bản và chủ phụ trách. |
| Nội dung vận hành | Mẫu bản nháp chiến dịch, nhật ký quyết định, cảnh báo web, bản rút gọn cho SMS/email và thông báo nội bộ. | Chủ vận hành. Kiểm tra bản nháp, quyết định và nội dung gửi có cùng định danh hồ sơ và đúng phạm vi đã duyệt. |
| Nội dung bàn giao | Bộ ca demo, hướng dẫn cấu hình, tài liệu vai user/ops, báo cáo chất lượng, lịch cập nhật tri thức, hướng dẫn ứng phó và quay lui. | PM + BE. Người mới thực hiện được luồng demo và tìm được người phụ trách từng dịch vụ. |

[Ánh xạ bước với người phụ trách và thư mục](TASKS.md#ánh-xạ-các-bước-vào-repo)

[Bàn giao MVP và điều kiện nghiệm thu từng bước](MVP_HANDOFF.md)

## Kiểm tra trước khi xác nhận cho người dùng MoMo

**Bài toán.** Khi đang chờ hoàn tiền hoặc xử lý đơn hàng, người dùng có thể nhận một mã QR qua Zalo, SMS hoặc sau cuộc gọi. Họ cần biết ngay thao tác tiếp theo sẽ khiến tiền đi đâu. MoMo đã có Nhãn người nhận ở bước chuyển khoản. PayPause bổ sung ngữ cảnh từ nội dung người dùng nhận được bên ngoài ví để giải thích vì sao yêu cầu đó đáng ngờ. [Nhãn người nhận và ví dụ dụ quét QR để lấy lại tiền](https://www.momo.vn/blog/nhan-nguoi-nhan-c198dt2858)

### Luồng demo ưu tiên

1. Trên PayPause, người dùng chọn **Tôi đang chờ nhận tiền** và gửi ảnh tin nhắn kèm mã QR mẫu. Nếu ảnh chứa cả hai, người dùng chỉ cần chọn một tệp.
2. Qwen Vision đọc lời nhắn bằng `prompts/ocr_v0.md`. Bộ kiểm tra QR xác định loại mã và số tiền nếu có. Bộ đối chiếu so sánh mục đích người dùng đã chọn với hành động mà mã yêu cầu. Qwen giải thích dựa trên câu trích từ tin nhắn và kết quả giải mã. Khi thiếu bằng chứng, giao diện hiện **Chưa xác định được mã này dùng để làm gì** và cho thử ảnh rõ hơn hoặc vào Trợ giúp.
3. Nếu dữ liệu mẫu cho thấy mã yêu cầu gửi 500.000 ₫, hiển thị **Bạn đang chờ nhận tiền. Nếu xác nhận, bạn sẽ chuyển đi 500.000 ₫.** Đặt **Dừng để xác minh** làm nút chính. Khi dừng, người dùng có thể mở **Trợ giúp MoMo** hoặc chọn **Hỏi người thân**. Nếu họ nói đã chuyển tiền, đưa lối vào Trợ giúp và kênh báo cáo chính thức lên trước. [Trợ giúp MoMo](https://www.momo.vn/hoi-dap) · [Kênh báo cáo lừa đảo](https://www.momo.vn/an-toan-bao-mat/bao-cao-lua-dao)

### Vai trò của người dùng, AI và chuyên viên

- Người dùng chọn mục đích giao dịch, xem bằng chứng và quyết định bước tiếp theo. Cảnh báo dùng câu ngắn, hiển thị được bằng trình đọc màn hình và có lối thoát ngay trên màn hình. Luồng mô phỏng giữ thao tác bình thường cho các ca không có mâu thuẫn hoặc tín hiệu rõ.
- AI đọc nội dung người dùng chủ động gửi, trích bằng chứng và đề xuất thao tác phù hợp. Quy tắc quyết định khi nào hiện cảnh báo về mâu thuẫn giữa mục đích khai báo và thông tin đọc được từ mã. Ca mơ hồ giữ trạng thái **Cần xác minh**.
- Người thân có thể xem bản tóm tắt hết hạn sau 24 giờ. Dùng luồng chia sẻ hiện có cho bản đầu. Nếu bổ sung lý do cảnh báo vào bản chia sẻ, cho người dùng xem trước và chỉ đưa tín hiệu đã che thông tin cá nhân.
- Chuyên viên duyệt các báo cáo mà người dùng đồng ý gửi. Agent hỗ trợ gom các ca tương tự và soạn giải thích. Chuyên viên xác minh trước khi cập nhật quy tắc hoặc nội dung cảnh báo. Tái sử dụng Qwen4-Max, bộ kiểm tra QR và bàn làm việc vận hành của PayPause.

### Thứ tự xây và tiêu chí nghiệm thu

| Bước | Bàn giao | Cách kiểm tra |
|---|---|---|
| 1. Mô phỏng quyết định | Màn hình PayPause với lựa chọn mục đích, bằng chứng và cảnh báo ngay trước xác nhận mô phỏng | Thử QR yêu cầu chuyển tiền trong ngữ cảnh hoàn tiền, QR thanh toán bình thường và ảnh QR mờ. Cảnh báo đúng mâu thuẫn, ca bình thường đi tiếp, ca mờ có đường xác minh. |
| 2. Kết nối người hỗ trợ | Nút Trợ giúp MoMo, chia sẻ tóm tắt, quy trình duyệt hồ sơ trong bàn làm việc vận hành | Mở đúng nguồn trợ giúp. Xác nhận bản chia sẻ hết hạn sau 24 giờ và người gửi thấy nội dung trước khi chia sẻ. Hồ sơ chỉ được tạo khi người dùng đồng ý. |
| 3. Kiểm thử với người dùng | So sánh cách hiển thị điểm rủi ro hiện tại với cảnh báo chỉ rõ tiền sẽ chuyển đi hay về và bước tiếp theo | Thử với ít nhất 10 người dùng MoMo, đổi thứ tự hai giao diện và dùng các ca tương đương. Mục tiêu ban đầu là ít nhất 8/10 người tự nhận ra đang chuẩn bị gửi tiền và thời gian trung vị để chọn cách xác minh tối đa 20 giây. Ghi cả số người bị gián đoạn ở ca hợp lệ. Lưu kết quả vào `docs/USER_TESTS.md`. |
| 4. Chuẩn bị thử nghiệm với MoMo | Đề xuất vị trí đặt tính năng, dữ liệu tối thiểu phải dùng và cách đo kết quả | Chỉ thử nghiệm trên luồng MoMo thật khi có thỏa thuận về quyền truy cập, bảo mật dữ liệu và phạm vi triển khai. Bản demo dùng dữ liệu giả lập. |

Sau ca QR, ưu tiên thử ca giả danh hỗ trợ MoMo yêu cầu OTP qua cuộc gọi hoặc dẫn sang link ngoài. Cảnh báo trích đúng yêu cầu trong tin nhắn hay bản chép và đưa người dùng tới Trợ giúp chính thức. [Cảnh báo cuộc gọi mạo danh MoMo](https://www.momo.vn/blog/mao-danh-nhan-vien-momo-qua-cuoc-goi-cach-nhan-c198dt2675)

## Phát hiện chủ động website mạo danh MoMo

PayPause đã có cổng phân tích tên miền, RDAP, dữ liệu đối chiếu, ảnh xem trước, đọc biểu mẫu tĩnh và bàn làm việc chuyên viên. Mở rộng luồng này để phát hiện sớm trang giả mạo MoMo và nối kết quả đã duyệt về tính năng **Kiểm tra trước khi xác nhận**. Các bước dưới đây là đề xuất triển khai dựa trên mô tả BrandShield, dùng quy tắc, Qwen4-Max và mã nguồn PayPause hiện có. [Luồng URL hiện tại](STATUS.md#url-security-agent)

### Nguồn ứng viên

| Nguồn | Cách đưa vào PayPause |
|---|---|
| `QUICK_CHECK` | Tái sử dụng kiểm tra URL do người dùng nhập. |
| `QR_GATEWAY` | Dùng tên miền từ QR liên kết và đích chuyển hướng công khai đã qua cổng kiểm tra. Giữ kết luận về chiều tiền của VietQR độc lập với đánh giá website. |
| `CSKH_REPORT` | Dùng báo cáo PayPause có đồng ý của người gửi. Thử nguồn CSKH của MoMo bằng dữ liệu giả lập trước, rồi kết nối khi được cấp quyền. |
| `THREAT_INTEL` | Tái sử dụng nguồn đã cấu hình. Ghi rõ nguồn nào khớp chính xác URL, nguồn nào chỉ đối chiếu tên miền và thời điểm dữ liệu được cập nhật. |
| `CT_LOGS` | Bổ sung tác vụ đọc dữ liệu chứng chỉ công khai, lọc theo tên thương hiệu cần bảo vệ, gộp bản ghi trùng và đưa ứng viên vào hàng đợi chuyên viên. Chứng chỉ mới chỉ là tín hiệu để ưu tiên kiểm tra. [Certificate Transparency](https://www.rfc-editor.org/rfc/rfc9162.html) |

### Ba nhóm bằng chứng và điều kiện kết luận

1. **Tên miền.** Dùng lại Public Suffix List, quy tắc tên miền tương tự và RDAP. Thêm danh sách tên miền chính thức và đối tác đã xác minh, với người duyệt và ngày rà. Điểm tương đồng hoặc tuổi tên miền phục vụ xếp hàng và cần được đối chiếu với ngữ cảnh trang.
2. **Giao diện.** Dùng ảnh người dùng gửi hoặc ảnh xem trước từ cổng thu thập theo phạm vi được phép. Qwen Vision hỗ trợ mô tả dấu hiệu nhận diện, như tên thương hiệu và lời yêu cầu xác minh tài khoản. Vị trí logo là hạng mục sau, chỉ hiển thị khi có vùng được kiểm chứng. Bảo vệ tác vụ thu thập bằng cô lập mạng và kiểm tra đích chuyển hướng, dùng phiên không có cookie người dùng, loại tham số nhạy cảm trước khi lưu và chỉ đọc các trang công khai trong phạm vi cho phép. [Hướng dẫn phòng SSRF của OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
3. **Biểu mẫu.** Dùng bộ đọc tĩnh hiện có để ghi nhận trường OTP, mật khẩu, dữ liệu thẻ và đích gửi biểu mẫu. Đối chiếu biểu mẫu với tên miền, mục đích trang và danh sách đã xác minh để giảm báo nhầm với đăng nhập hợp lệ hoặc bài viết cảnh báo. Bằng chứng lưu gồm loại trường và tên miền đích. Quy trình chỉ đọc biểu mẫu, không nhập hoặc gửi dữ liệu.

Kết luận tự động dùng quy tắc có phiên bản và trả kèm nguồn bằng chứng. Qwen viết lời giải thích từ bằng chứng đã có. Chuyên viên lưu quyết định riêng cùng lý do và lịch sử duyệt.

| Trạng thái | Điều kiện và hành động |
|---|---|
| `BENIGN` | Các kiểm tra bắt buộc đã chạy và chưa thấy dấu hiệu mạo danh. Giao diện ghi **Chưa thấy dấu hiệu mạo danh trong phạm vi kiểm tra**. |
| `ABSTAIN_NEEDS_REVIEW` | Thiếu dữ liệu quan trọng, bằng chứng mâu thuẫn hoặc chỉ có tín hiệu yếu. Giao diện ghi **Cần xác minh** và chỉ rõ dữ kiện còn thiếu. |
| `IMPOSTOR` | Có bằng chứng đủ mạnh về việc mượn danh thương hiệu và yêu cầu nhạy cảm, ví dụ giao diện tự nhận là MoMo trên miền ngoài danh mục đã xác minh và biểu mẫu gửi OTP đến miền không được xác minh. Ứng viên vào hàng duyệt. Chỉ quyết định đã duyệt mới kích hoạt cảnh báo trong PayPause. |

### Thứ tự xây dựng

| Bước | Bàn giao và kiểm tra |
|---|---|
| 1. Cổng kết luận có bằng chứng | Chạy ba trạng thái trên bộ ca gồm website chính thức, đối tác hợp lệ, bài báo nhắc MoMo, trang giả lập xin OTP và ca mất nguồn. Kiểm tra mỗi kết luận có căn cứ và nội dung Qwen không đổi trạng thái. |
| 2. Phát hiện trước khi có báo cáo | Nhập lô chứng chỉ công khai mẫu và nguồn tình báo đã cấu hình, gộp tên miền trùng, lưu nguồn và đưa ứng viên có dấu hiệu vào hàng duyệt. Đo thời gian từ khi nhận ứng viên đến khi chuyên viên xem hồ sơ, số trùng và tỷ lệ chuyển duyệt. |
| 3. Nối cảnh báo với người dùng | Chuyên viên xác minh một website giả lập. Khi người dùng gửi ảnh tin nhắn hoặc QR liên kết trỏ đến website đã duyệt, PayPause giải thích dấu hiệu và hiển thị **Dừng để xác minh** cùng Trợ giúp MoMo. Kiểm tra ca bị bác và ca đang chờ duyệt không phát cảnh báo cộng đồng. |
| 4. Bàn giao cho đối tác | Chuẩn bị gói bằng chứng đã che, gồm tên miền, nguồn, thời điểm và lịch sử duyệt. Việc chia sẻ IOC, cập nhật danh sách chặn MoMo và gửi yêu cầu gỡ website cần thỏa thuận với đội vận hành có thẩm quyền. |

**Đã thực hiện trong PayPause.** Cổng ba trạng thái, nhận lô theo năm nhãn nguồn, gộp theo hostname, đối chiếu HTML tĩnh và chữ từ ảnh, duyệt hoặc rút cảnh báo, xuất JSON và nối kết quả đã duyệt vào Website, VietQR và Kiểm tra trước khi xác nhận. Kiểm thử bao gồm trang chính thức, bài hướng dẫn, hồ sơ thiếu bằng chứng, nền tảng dùng chung, phân quyền và hết hạn cảnh báo. Nguồn CT chạy bằng lô đã xuất. Lịch thu thập CT trực tiếp và kết nối hệ thống MoMo thuộc bước triển khai với đối tác. [Hướng dẫn demo](MVP_HANDOFF.md#demo-phát-hiện-sớm-website-mạo-danh-momo)

---

## Prompt mẫu theo vai

**PM (mở đầu ngày):** `/daily-standup 5` → "Dựa trên STATUS và PLAN, chia việc ngày mai thành task ≤ 1 ngày, mỗi task có chủ, file được sửa, tiêu chí xong."

**AI (sửa theo lỗi):** "Đọc báo cáo eval mới nhất. Nhóm các mẫu bỏ sót theo nguyên nhân. Đề xuất một thay đổi nhỏ nhất cho prompt hoặc luật, viết prompts/analyzer_vN.md, chạy eval có --compare, dán bảng chỉ số."

**BE (endpoint mới):** "Thêm POST /v1/ops/campaigns/{id}/decision theo hợp đồng trong agent backend-engineer. Viết test trước, chạy pytest, dán kết quả. Dùng context7 cho FastAPI và Supabase."

**FE (giao diện):** "Làm thẻ kết quả theo analysis.schema.json. Chụp màn hình bằng Playwright ở khổ 390px và 1280px, liệt kê khác biệt so với yêu cầu trong agent frontend-engineer rồi sửa."

**QA (phản biện):** "Dùng subagent eval-qa: tạo 10 đầu vào kiểu BGK chưa có trong eval, chạy qua API public, ghi eval/adversarial-&lt;ngày&gt;.md với kết quả và nhận xét."

**Rà soát độc lập trước merge:** "Dùng subagent security-reviewer rà diff của nhánh này so với main. Chỉ báo vấn đề ảnh hưởng an toàn hoặc yêu cầu."
