# Nhật ký quyết định

`Ngày | Quyết định | Lý do / bằng chứng | Người quyết`

| Ngày | Quyết định | Lý do / bằng chứng | Người quyết |
|---|---|---|---|
| (ngày 0) | Đề tài lõi: Trước Khi Chuyển + bàn làm việc vận hành | Điểm 4,7/5 trong bảng chấm 6 đề tài | PM |
| (ngày 0) | Kế hoạch 14 ngày, Should tối đa 2 mục | Hạn nộp khoảng 2 tuần | PM |
| 2026-11-24 | Persona chính là người giao dịch online 20–40 tuổi; người 50+ là persona phụ (slide + Should #2) | Nhiều link/QR/đặt cọc, đúng luồng demo; vẫn giữ ràng buộc chữ ≥ 18px và 1 hành động chính | PM |
| 2026-11-24 | Luồng demo chính là **ảnh chụp tin nhắn**; link và QR đi cùng pipeline nhưng không phải luồng chính | BGK tự chụp bằng điện thoại của họ nên khó dàn dựng; sau bước đọc ảnh xử lý như văn bản | PM |
| 2026-11-24 | Must = 7 mục, thêm M7 "tra bằng chứng: danh sách đen nội bộ + domain_check + Google Safe Browsing"; giữ nút báo cáo trong Must | Có trích dẫn bằng chứng mới chống được phản biện "AI đoán"; domain_check đã có trong kit | PM |
| 2026-11-24 | RDAP/whois hạ từ Must xuống Could | Tên miền .vn thường không tra được, tỉ lệ dữ liệu trống cao | PM |
| 2026-11-24 | Should: S1 QR sạch (ưu tiên), S2 chế độ người thân **bản rút gọn** = link chia sẻ tóm tắt 2 câu, đã che PII, hết hạn 24h; bot Telegram xuống Could | Tiết kiệm ~1 ngày BE, bỏ phụ thuộc bên thứ ba, vẫn giữ được câu chuyện persona 50+ | PM |
| 2026-11-24 | Mốc độ trễ tách theo loại đầu vào: văn bản p95 ≤ 6s, ảnh p95 ≤ 12s (recall ≥ 0.90, báo nhầm ≤ 0.10 giữ nguyên) | Vision + 3 lần tra bằng chứng không thể vào 8s; ép 8s sẽ khiến đội cắt bước tra bằng chứng | PM |
| 2026-11-24 | Màn chờ hiện tiến trình thật 3 chặng, KHÔNG hiện kết luận rủi ro sơ bộ rồi đổi sau | Đổi kết luận giữa luồng làm mất tin cậy và dễ bị BGK bắt lỗi | PM |
| 2026-11-24 | Chỉ số workspace đo thật: 5 chiến dịch × 8–10 báo cáo, 2 người khác nhau, đo cả thời gian lẫn số quyết định đúng; phỏng vấn 1 người vận hành/CSKH để xác nhận; slide ghi "thử nghiệm nội bộ, 5 chiến dịch" | Tránh số liệu tự khen không kiểm chứng được | PM |
| 2026-11-24 | Mục 1 brief dùng số 6.000 tỷ/11 tháng 2025 (Bộ Công an qua VietNamNet) + SIMO 28/9/2026 (CafeF); không dùng con số 8.000 tỷ cùng lúc | Một con số một slide, luôn kèm nguồn; tránh BGK bắt lỗi số liệu không nhất quán | PM |
| 2026-11-24 | Mốc "< 10 giây" của ngày 2 chỉ là 1 ảnh/1 lần; p95 chính thức áp từ ngày 4 | Ngày 2 chưa đủ mẫu để tính p95; không để mốc giả làm đội cắt bước tra bằng chứng | PM |
| 2026-11-24 | ~~Hợp đồng BE↔AI: `analyzer.analyze(text, image_bytes) -> dict`~~ **(thay bằng dòng dưới cùng ngày)** | Thiếu tham số mime | PM |
| 2026-11-24 | Rủi ro số 1 là sập/hết quota lúc BGK thử → bắt buộc có "chế độ hạn chế" (luật + danh sách đen) thay vì trang lỗi | Sập lúc chấm là mất trắng; rủi ro số 2 (vision đọc tiếng Việt sai) sẽ biết ở ngày 4 | PM |
| 2026-11-24 | Hợp đồng gửi ảnh: `POST /v1/analyze` nhận JSON `{text, image_base64, image_mime: image/png\|image/jpeg}`, ảnh ≤ 5 MB (byte gốc); `run_eval.py` gửi đúng dạng này, `--baseline` coi mẫu ảnh là "không đọc được" (low) | Ảnh có thể chứa PII nên không dùng URL ngoài; trần 5 MB để eval và API từ chối giống nhau. Bằng chứng: `tests/test_kit_scripts.py::test_run_eval_sends_image_payload_and_reports_p95_by_type` (16 test pass) | **PM** (xác nhận 2026-11-24) |
| 2026-11-24 | PM xác nhận 4 điểm eval-qa tự thêm: (1) bỏ `image_url`, (2) p95 tách 6s/12s, (3) ảnh hỏng/quá cỡ trả 4xx chứ không trả `low`, (4) trường `transcript` không gửi cho analyzer | Ảnh có PII nên không dùng URL ngoài; trả `low` cho ảnh không đọc được là nguy hiểm nhất (người dùng tưởng an toàn); transcript chưa trong phạm vi vòng này | PM |
| 2026-11-24 | `POST /v1/analyze` dùng **JSON base64**, KHÔNG dùng multipart: `{"text": str\|"", "image_base64": str?, "image_mime": "image/png"\|"image/jpeg"?}`, ảnh ≤ 5 MB byte gốc; sai định dạng → 415, quá cỡ → 413, **thông báo tiếng Việt, không bao giờ trả `low`** | Khớp đúng `run_eval.py` đã chạy được (16 test pass), `scam-analyzer/SKILL.md` và dòng hợp đồng gửi ảnh ở trên — một dạng payload duy nhất cho cả eval và app | PM |
| 2026-11-24 | FE **nén ảnh phía trình duyệt** trước khi gửi: cạnh dài ≤ 1600px, JPEG | Ảnh điện thoại 4–12 MB sẽ đụng trần 5 MB và đẩy p95 ảnh vượt 12s; nén ở client rẻ hơn mọi cách khác | PM |
| 2026-11-24 | Hợp đồng BE↔AI (bản chốt): AI commit **hàm stub** `analyze(text: str\|None, image: bytes\|None, mime: str\|None) -> dict` trả JSON mẫu đúng schema, **trước 10:00 ngày 2**; BE nối endpoint vào stub, FE dùng chính JSON đó; AI thay ruột thật sau | Xóa toàn bộ thời gian chờ nhau trong ngày 2 — rủi ro số 1 của ngày 2; stub là hợp đồng chạy được, không phải tài liệu | PM |
| 2026-11-24 | Với đầu vào ảnh, "quote khớp đúng chuỗi" = khớp **văn bản đã đọc từ ảnh** (OCR/vision), không phải byte ảnh | Không thể khớp chuỗi vào ảnh; hậu kiểm trích dẫn vẫn phải chạy được cho luồng demo chính | PM |
| 2026-11-24 | Sửa mốc p95 trong `.claude/skills/gate-check/SKILL.md`, đổi `latency_p95_s` → `p95_text`/`p95_image` trong `.claude/hooks/session-context.sh`, sửa đường dẫn `dataset-guide.md`, thêm ghi chú Windows vào CLAUDE.md | eval-qa phát hiện 4 chỗ lệch sau khi đổi mốc p95; để nguyên thì `/gate-check G2` sẽ chấm sai cổng | PM |
