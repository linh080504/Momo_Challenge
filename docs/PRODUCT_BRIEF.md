# Product brief — Trước Khi Chuyển

**Trạng thái:** chốt ngày 1 (2026-11-24) qua phỏng vấn PM · **Người chốt:** PM
**Nguyên tắc:** Must là bất khả xâm phạm. Should tối đa 2 mục. Không lùi hạn, chỉ cắt phạm vi.

---

## 1. Vấn đề

Lừa đảo trực tuyến gây thiệt hại hơn 6.000 tỷ đồng trong 11 tháng năm 2025 (Bộ Công an, qua VietNamNet:
https://vietnamnet.vn/toi-pham-mang-se-dung-nhieu-cong-nghe-deepfake-de-lua-dao-trong-nam-2026-2479714.html).
Cảnh báo đúng lúc có tác dụng: đến 28/9/2026, hệ thống SIMO của NHNN đã phát 5,6 triệu lượt cảnh báo,
1,9 triệu lượt khách dừng giao dịch, giữ lại hơn 6.300 tỷ đồng (CafeF:
https://cafef.vn/hon-19-trieu-luot-khach-hang-dung-giao-dich-sau-canh-bao-gian-lan-18826100811053583.chn).
Nhưng ngân hàng và ví chỉ thấy "phút thứ 89", lúc người dùng bấm chuyển tiền; 88 phút dụ dỗ trước đó
diễn ra trên Zalo, Facebook, điện thoại. Trước Khi Chuyển can thiệp sớm hơn: ngay khi người dùng
nghi ngờ một tin nhắn, link hay mã QR.

> **Ghi chú cho slide:** nguồn khác ghi hơn 8.000 tỷ cho cả năm 2025 (MoMo dẫn Bộ Công an).
> Chỉ dùng **một** con số, **luôn kèm nguồn**. Không trộn hai con số trong cùng một slide.

---

## 2. Người dùng

| Persona | Bối cảnh | Việc cần làm | Thành công nghĩa là |
|---|---|---|---|
| **P1 — CHÍNH: Người giao dịch online 20–40 tuổi** | Mua/bán qua Facebook, Zalo, sàn; nhận link lạ, mã QR, tin "việc làm thêm"; sắp đặt cọc | Dán/chụp cái vừa nhận, biết trong vài giây có nên chuyển tiền hay không, và nếu không thì vì sao | Dừng lại trước khi chuyển, hoặc tự tin chuyển sau khi kiểm tra; báo cáo lại trong 1 nút |
| **P2 — PHỤ: Người 50+, ít kinh nghiệm số** | Con cháu không ở cạnh; nhận cuộc gọi/tin nhắn giả mạo | Hiểu kết quả không cần giải thích; hỏi người thân khi vẫn lưỡng lự | Đọc hiểu kết quả 3 dòng; gửi được tóm tắt cho người thân qua Zalo/Messenger |
| **P3 — Chuyên viên vận hành fintech (lớp workspace)** | Hàng chờ báo cáo từ người dùng, công cụ hiện tại là bảng tính + tra tay | Gom báo cáo rời thành **chiến dịch**, xem bằng chứng, duyệt/bác bỏ, phát cảnh báo | Xử lý 1 chiến dịch nhanh hơn rõ rệt so với thủ công, có nhật ký duyệt để hậu kiểm |

**Ràng buộc thiết kế chéo persona:** dù P1 là trung tâm, giao diện phải dùng được cho P2 — chữ ≥ 18px,
**một hành động chính** trên mỗi màn, kết quả gói trong **3 dòng** trước khi muốn xem chi tiết.
P2 là nhân vật của câu chuyện trên slide/video và là lý do tồn tại của Should #2.

---

## 3. Luồng chính BGK sẽ thử (6 bước)

Đầu vào số 1 phải hoàn hảo: **ảnh chụp tin nhắn do BGK tự chụp bằng điện thoại của họ.**

1. BGK mở URL public trên điện thoại → **tải ảnh chụp tin nhắn** (cùng ô nhập đó cũng dán được văn bản thuần).
2. Màn chờ hiện **tiến trình thật**, ví dụ: `Đã đọc ảnh → STK 0123****89, link xyz.top → Đang tra bằng chứng…`
3. **Thẻ kết quả**: mức nguy cơ · 3 dấu hiệu, mỗi dấu hiệu có trích dẫn từ đúng đoạn trong ảnh · câu hỏi kiểm chứng ·
   câu "Kết quả do AI phân tích và có thể sai. Hãy xác minh qua số tổng đài chính thức trước khi chuyển tiền."
4. BGK bấm **Báo cáo** (1 nút).
5. BGK đăng nhập tài khoản ops → báo cáo đó đã **được gom vào một chiến dịch** cùng các báo cáo trùng STK/SĐT/tên miền →
   xem hồ sơ chiến dịch do AI viết → **bấm Duyệt** (có nhật ký ghi ai duyệt, lúc nào).
6. BGK quay lại vai người dùng, gửi lại đầu vào tương tự → **nhận cảnh báo đã được người duyệt xác nhận**.

**Sau bước đọc ảnh, mọi đầu vào đi chung một pipeline.** Link và QR dùng cùng pipeline đó nhưng **không phải luồng demo chính**.

---

## 4. Phạm vi

### Must (7 mục — bất khả xâm phạm)

| # | Must | Chủ chính |
|---|---|---|
| M1 | Một ô nhập nhận **ảnh + văn bản**; ảnh được đọc bằng vision, sau đó xử lý như nhau | frontend-engineer · backend-engineer |
| M2 | Phân tích trả **JSON đúng `analysis.schema.json`**: mức nguy cơ + **3 dấu hiệu có trích dẫn** + câu hỏi kiểm chứng | ai-engineer |
| M3 | **Nút báo cáo** 1 bước từ thẻ kết quả | frontend-engineer · backend-engineer |
| M4 | `/ops`: **gom chiến dịch + con người duyệt + nhật ký duyệt**; duyệt rồi mới ảnh hưởng người dùng khác | cả đội |
| M5 | **Ẩn danh PII** (`pii-guard`) trước mọi lần gửi LLM/bên thứ ba; không log văn bản chưa mask | security-reviewer rà |
| M6 | **Chạy thật trên URL public** + **2 tài khoản test** (user, ops) cho BGK tự thử | backend-engineer |
| M7 | **Tra bằng chứng**: danh sách đen nội bộ + `domain_check.py` (có trong kit) + **Google Safe Browsing** | ai-engineer · backend-engineer |

### Should (tối đa 2, theo thứ tự — nếu chỉ kịp 1 thì giữ S1)

- **S1 — Đọc VietQR + "QR sạch" (ưu tiên cao hơn):** giải mã ảnh QR, hiện các trường người nhận, so khớp người nhận
  trong QR với nội dung tin nhắn; gắn nhãn "QR sạch" **chỉ khi** rủi ro thấp **và** người dùng đã xác nhận người nhận.
- **S2 — Chế độ người thân (bản rút gọn):** sinh **link chia sẻ** chứa **tóm tắt 2 câu**, đã che STK/SĐT,
  **hết hạn sau 24 giờ**; người dùng tự gửi qua Zalo/Messenger bằng **nút chia sẻ của hệ điều hành**. Không có bot.

### Could (chỉ làm nếu G2 đạt sớm và không chạm Must)

- Bot Telegram cho người giám hộ (bản đầy đủ của S2).
- RDAP/whois tra tuổi tên miền — *hạ xuống Could vì tên miền `.vn` thường không tra được*.
- Phân tích **ghi âm** cuộc gọi.
- Số liệu nội bộ của `/ops`: biểu đồ xu hướng chiến dịch.

### Won't (vòng này — nói rõ với BGK)

- AI tự chuyển tiền hoặc tự chặn giao dịch.
- AI tự đưa thực thể vào danh sách đen mà không có người duyệt.
- Tích hợp thật với ngân hàng / cổng thanh toán.
- App di động cài đặt được (chỉ web responsive).
- Demo kịch bản cứng, đầu vào cài sẵn.

---

## 5. Chỉ số thành công

### 5.1 Chất lượng AI (nguồn: `eval/reports/latest.json`, ≥ 100 mẫu, ≥ 20 mẫu ảnh)

| Chỉ số | Cổng |
|---|---|
| Recall (bắt được lừa đảo) | **≥ 0.90** |
| Báo nhầm (false positive) | **≤ 0.10** |
| p95 độ trễ — **đầu vào văn bản** | **≤ 6s** |
| p95 độ trễ — **đầu vào ảnh** | **≤ 12s** |
| Holdout (`eval/holdout.jsonl`, 20 mẫu người tạo tay) | không tụt quá 0.05 recall so với dev set |

**Quy ước trải nghiệm chờ:** trong lúc chờ, hiện **tiến trình thật** (đã đọc ảnh → thực thể đã trích → đang tra bằng chứng).
**KHÔNG hiện kết luận rủi ro sơ bộ rồi đổi sau** — đổi kết luận giữa luồng làm người dùng mất tin và dễ bị BGK bắt lỗi.

### 5.2 Người dùng thật

- **≥ 10 người** đã thử mà không cần hướng dẫn (ngày 8: 5 người · ngày 9: thêm 5 người), ghi `docs/USER_TESTS.md`.

### 5.3 Workspace — thời gian xử lý 1 chiến dịch (trụ cột "Future Workspace")

Phương pháp **đo thật + phỏng vấn xác nhận**:

- **Đo:** 5 chiến dịch, mỗi chiến dịch 8–10 báo cáo. **Hai người khác nhau**: một người làm thủ công
  (bảng tính + tra tay), một người dùng `/ops`. Đo **cả thời gian lẫn số quyết định đúng** (không chỉ nhanh hơn mà phải đúng hơn hoặc bằng).
- **Xác nhận:** phỏng vấn **1 người từng làm vận hành/CSKH** để kiểm tra quy trình thủ công mô phỏng có giống thực tế.
- **Trên slide ghi rõ:** *"thử nghiệm nội bộ, 5 chiến dịch"* — không gọi là nghiên cứu.
- Kết quả: thủ công **__ phút/chiến dịch** → có AI **__ phút/chiến dịch**; quyết định đúng **__/5** vs **__/5**.
  *(điền từ `docs/USER_TESTS.md`, hạn ngày 11)*

---

## 6. Câu hỏi đã gửi BTC / câu trả lời

| Câu hỏi | Ngày gửi | Trả lời |
|---|---|---|
| BGK có tự thử sản phẩm trên URL public, hay chỉ xem video demo? | ngày 1 | *(chờ)* |
| Có yêu cầu nộp mã nguồn mở hay repo riêng tư? | ngày 1 | *(chờ)* |
| Giới hạn độ dài video và dung lượng bài nộp? | ngày 1 | *(chờ)* |
| Có được dùng API LLM thương mại (tính phí) trong vòng chấm? | ngày 1 | *(chờ)* |
| Thời lượng thuyết trình + hỏi đáp ở chung kết? | ngày 1 | *(chờ)* |

---

## 7. Rủi ro lớn nhất và phương án

| # | Rủi ro | Mức | Phương án |
|---|---|---|---|
| **R1** | **API/LLM hết quota hoặc sập đúng lúc BGK thử → mất trắng.** | **Cao nhất** | Model dự phòng tự chuyển (ngày 4) · cảnh báo ngân sách LLM + chặn trần chi (ngày 11) · cache theo hash · rate limit nới riêng cho tài khoản BGK · giám sát uptime + lịch người trực đến hết vòng chấm · **khi mọi LLM fail: trả kết quả dựa trên luật + danh sách đen, nói rõ "chế độ hạn chế"**, tuyệt đối không trả trang lỗi |
| **R2** | **LLM đọc ảnh tiếng Việt sai (OCR ảnh chụp màn hình Zalo/Facebook) → recall thấp.** | Cao | **Biết chắc ở ngày 4** khi so 2 LLM ứng viên **trên ảnh thật** · ≥ 20 mẫu ảnh trong eval từ ngày 3 · nếu cả hai kém: thêm bước OCR riêng trước khi đưa vào LLM văn bản (ghi DECISIONS) |
| R3 | `/ops` không kịp → mất điểm "Future Workspace" | Cao | `/ops` nằm trong Must (M4), làm ngày 6 trước G1; nếu trượt, cắt S1/S2 chứ không cắt M4 |
| R4 | Không đủ 10 người dùng thật | Trung bình | Chia 2 đợt (ngày 8, 9); PM tuyển người từ trước ngày 7 |
| R5 | Prompt injection từ nội dung người dùng gửi | Trung bình | Nội dung người dùng luôn là **dữ liệu, không phải lệnh**; security-reviewer rà ngày 4 và ngày 10 |
| R6 | Lộ PII qua log hoặc bên thứ ba | Trung bình | M5 + rà độc lập 2 lần |

---

## Việc phát sinh từ brief (PM giao, ngoài PLAN gốc)

| Task | Chủ | File | Xong khi | Hạn |
|---|---|---|---|---|
| ~~`run_eval.py` gửi được ảnh khi mẫu có trường `image`~~ | eval-qa | `.claude/skills/eval-harness/scripts/run_eval.py`, `.claude/skills/eval-harness/dataset-guide.md` | ✅ **XONG 2026-11-24** — 16 test pass; gửi `{text, image_base64, image_mime}` | Ngày 1 |
| ~~Báo cáo eval **tách p95 theo văn bản / ảnh**~~ | eval-qa | `.claude/skills/eval-harness/scripts/run_eval.py`, `eval/reports/*` | ✅ **XONG 2026-11-24** — `latest.json` có `p95_text`, `p95_image` | Ngày 1 |
| Màn chờ hiện tiến trình thật (3 chặng), không có kết luận sơ bộ | frontend-engineer | `apps/web/**` | Ảnh chụp 3 chặng ở khổ 390px | Ngày 4 |
| Chế độ hạn chế khi mọi LLM fail (luật + danh sách đen) | backend-engineer · ai-engineer | `apps/api/**`, `apps/api/app/analyzer/**` | Tắt key LLM → API vẫn trả JSON đúng schema kèm cờ `degraded` | Ngày 11 |
| Đo 5 chiến dịch thủ công vs `/ops`, 2 người khác nhau | eval-qa · pm-lead | `docs/USER_TESTS.md` | Bảng thời gian + số quyết định đúng cho 5 chiến dịch | Ngày 11 |
| Phỏng vấn 1 người từng làm vận hành/CSKH | pm-lead | `docs/USER_TESTS.md` | Biên bản phỏng vấn, xác nhận quy trình thủ công | Ngày 9 |
| ~~2–3 số liệu có nguồn cho mục 1~~ | pm-lead | `docs/PRODUCT_BRIEF.md` | ✅ **XONG 2026-11-24** — 2 số liệu có link nguồn | Ngày 1 |

Chia việc chi tiết theo ngày: `docs/TASKS.md`. 7 task trên đã được nhúng vào `docs/PLAN.md` đúng ngày cần làm.

## Phạm vi phiên bản nâng cấp PayPause AI

Người dùng có thể kiểm tra sáu dạng nội dung trước khi chuyển tiền gồm tin nhắn, ảnh chụp, URL, QR, ghi âm và biên lai. Kết quả giúp họ hiểu tín hiệu, xem bằng chứng và chọn cách xác minh. Chuyên viên vận hành có bản đồ chiến dịch, kết quả điều tra và bản nháp cảnh báo để ra quyết định.

- **Trải nghiệm hiện có ở bản local.** Kiểm tra tin nhắn, ảnh, URL, QR liên kết và VietQR. Biên lai hiển thị ảnh gốc, vùng chữ và sai khác nén JPEG để đối chiếu. Luồng ghi âm có giao diện và adapter Whisper, cần cấu hình môi trường để chạy nhận dạng thật.
- **Độ tin cậy của kết quả.** Tín hiệu kỹ thuật và bằng chứng đã xác minh có nguồn rõ ràng. Dữ liệu ghi âm và ảnh được xử lý theo cấu hình của hệ thống. Kết quả từ ảnh biên lai thể hiện trạng thái `unverified` đến khi có đối chiếu từ nguồn giao dịch được cấp quyền.
- **Trải nghiệm chuyên viên.** Supervisor điều phối sáu tác nhân đọc bằng chứng, tra tín hiệu, xử lý thông tin pháp y, nối chiến dịch, đề xuất bảo vệ và soạn nháp. Chuyên viên quyết định duyệt hoặc bác bỏ, có nhật ký và quyền theo vai. Cảnh báo đa kênh và xác minh giao dịch phụ thuộc nguồn dịch vụ được cấp quyền.
- **Điều kiện mở rộng.** Chỉ số chính của MVP vẫn là recall, báo nhầm và p95 tách theo loại đầu vào. Thêm chất lượng OCR/ASR, vùng bằng chứng biên lai, độ hiệu chuẩn, gộp chiến dịch, tỷ lệ gọi Deep Path, chi phí mỗi ca và thời gian ra quyết định của chuyên viên. Số liệu công bố cần gắn phiên bản, tập dữ liệu và phạm vi đánh giá.

[Kiến trúc](PLAN.md#lộ-trình-nâng-cấp-paypause-ai) · [Kế hoạch xây dựng từng bước](PLAN.md#kế-hoạch-xây-dựng-từng-bước) · [Kịch bản nghiệm thu](USER_TESTS.md#kịch-bản-nghiệm-thu-bản-nâng-cấp)

### Hợp đồng sáu đầu vào và hai luồng sản phẩm

**Người dùng** mở trang kiểm tra, dán nội dung hoặc chọn tệp, xem tiến trình và nhận một kết quả cuối. Từ kết quả, họ xác minh qua nguồn chính thức, chia sẻ tóm tắt 24 giờ hoặc đăng nhập để báo cáo. Người dùng mở `/qr` khi cần đọc ảnh QR và đối chiếu thông tin người nhận.

**Chuyên viên** đăng nhập `/ops`, mở hàng đợi và chọn chiến dịch, đối chiếu đồ thị, tín hiệu và bản nháp. Có thể sửa nhóm thủ đoạn trước khi duyệt hoặc bác bỏ. API ghi quyết định cùng phiên bản hồ sơ. Người dùng nhận cảnh báo khi lượt kiểm tra sau trùng thực thể trong hồ sơ đã duyệt.

| Đầu vào | Trường JSON và giới hạn | Xử lý và bằng chứng | Lỗi cần thử |
|---|---|---|---|
| Tin nhắn | `text`, tối đa 12.000 ký tự | Trích thực thể, đối chiếu luật/nguồn, hiển thị câu chữ và lý do | Thiếu nội dung hoặc vượt giới hạn trả 422. |
| Ảnh chụp | `image_base64`, `image_mime`, mặc định `image_kind: "image"`. PNG/JPEG tối đa 5 MiB và 16 triệu pixel | OCR tiếng Việt, sau đó phân tích văn bản. Tiến trình `image_read` | Sai loại trả 415. Quá cỡ trả 413. Ảnh hỏng hoặc không đọc được chữ trả 422. |
| URL | `url`, tối đa 2.000 ký tự. Có thể dán link trong `text` | Chuẩn hóa tên miền và hiển thị `url_checks`; có nguồn tra cứu khi cấu hình | Địa chỉ không hợp lệ ở trường `url` trả 422. |
| QR | `/v1/qr/parse` nhận `payload` tối đa 1.024 ký tự hoặc ảnh QR. Analyzer nhận `qr_payload` đã giải mã tối đa 2.000 ký tự | `/v1/qr/parse` trả `kind: "url"` hoặc `"payment"`. Analyzer phát `qr_read`; phía người dùng thấy loại mã, tên miền hoặc thông tin nhận đã che | Mã hỏng/không đọc được trả 422. Tạo lại yêu cầu QR thanh toán rủi ro thấp và xác nhận, nếu thiếu trả 409. |
| Ghi âm | `audio_base64`, WAV PCM mono 16 bit, 16 kHz, tối đa 45 giây và 2.000.000 byte | Whisper cục bộ, phát `audio_read` và chuyển bản chép lời qua luồng phân tích văn bản | Không đúng thông số trả 415. WAV lỗi hoặc quá thời lượng trả 422. Thiếu Whisper trả 503. |
| Biên lai | Cùng giới hạn ảnh, đặt `image_kind: "receipt"` và giữ tệp gốc trong giới hạn | `document` gồm vùng chữ OCR, vùng sai khác nén và `transaction_status: "unverified"` | Thiếu ảnh trả 422. Dùng các ca lỗi ảnh và ảnh nén để kiểm tra. |

`/v1/analyze` trả JSON theo `analysis.schema.json`. `/v1/analyze/stream` dùng `application/x-ndjson`. Các chặng trích xuất tùy đầu vào, sau đó có `entities`, `evidence` và một dòng `{result}`. Lỗi trước khi mở stream dùng HTTP cùng `detail`. Lỗi sau khi đã mở stream dùng một dòng cuối `{error, status}`. Request có thể kèm văn bản và tối đa một tệp ảnh hoặc ghi âm. `locale` mặc định `vi`. Tổng thân JSON tối đa 7.100.000 byte.

| Hành động | Khách | Người dùng | Chuyên viên |
|---|---|---|---|
| Phân tích tin nhắn/ảnh/URL/QR/ghi âm/biên lai | Có | Có | Có |
| Chia sẻ tóm tắt | Có, nếu kết quả tạo khi chưa đăng nhập | Có với kết quả của mình | Có với kết quả của mình |
| Gửi báo cáo có đồng ý, xóa các báo cáo thuộc tài khoản | Cần đăng nhập | Có | Có |
| Xem hồ sơ, sửa nhóm, duyệt/bác và xem phản hồi đã xác minh | Cần đăng nhập | Yêu cầu vai vận hành | Có |

Khoá báo cáo và chia sẻ là `analysis_id` có thời hạn 30 phút. Hồ sơ cập nhật trong lúc chuyên viên đang xem sẽ buộc tải lại trước khi duyệt bằng phiên bản mới. [Kịch bản nghiệm thu](USER_TESTS.md#kịch-bản-nghiệm-thu-bản-nâng-cấp)
