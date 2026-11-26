# Đánh giá MVP

- `dataset.example.jsonl` có 18 ví dụ tổng hợp. `prepare_smoke.py` tạo thêm 5 ảnh từ những ví dụ này để kiểm tra OCR. Tập sinh ra có các ca văn bản và ảnh trùng nội dung, phù hợp cho smoke test.
- QA đưa mẫu đã duyệt và ẩn danh vào `dataset.jsonl`, ảnh đã che thông tin vào `images/`, và lưu dữ liệu gốc ngoài Git. Dùng hướng dẫn gán nhãn ở [dataset-guide.md](../.claude/skills/eval-harness/dataset-guide.md).
- Tập chính thức gồm ít nhất 100 mẫu và 20 ảnh theo Product Brief. QA giữ riêng 20 mẫu holdout trong `holdout.jsonl` đến lúc chốt số liệu.
- Cổng chính thức dùng recall ≥ 0,90, báo nhầm ≤ 0,10, p95 văn bản ≤ 6 giây và p95 ảnh ≤ 12 giây. Ghi tỷ lệ mẫu tổng hợp cùng với kết quả.
- Harness ghi `last_run.json` sau mỗi lần chạy có báo cáo và cập nhật `latest.json` khi lượt gọi API đạt. Dùng `--out eval/generated/reports` cho mẫu smoke. Nếu chạy nhiều mẫu trên bản public, đăng nhập tài khoản thử và truyền tên biến token bằng `--token-env`.

## Chuẩn bị dữ liệu sáu đầu vào

Giữ bản gốc và dữ liệu có thông tin cá nhân ở nơi được cấp quyền. Mỗi bản dữ liệu đã rà có manifest ghi phiên bản, mô tả nguồn, mục đích được phép dùng, số mẫu mỗi nhãn, tỷ lệ tổng hợp và mã SHA-256 cho các tập. Lưu nhãn `scam` hoặc `legit`, nhóm thủ đoạn G1–G5 khi có, mã nhóm dùng khi tách tập, và vùng bằng chứng phù hợp với từng kênh. Gắn ca mơ hồ để chuyên viên rà trước khi chấm điểm chính thức.

| Kênh | Trường đầu vào cho `run_eval.py` | Nhãn hoặc dữ liệu đối chiếu cần có | Đơn vị ưu tiên cách ly giữa các tập |
|---|---|---|---|
| Tin nhắn | `text` | Nhãn, nhóm thủ đoạn, đoạn câu làm bằng chứng | Mẫu nội dung và chiến dịch |
| Ảnh chụp | `image`, `text` khi có nội dung đi kèm | Bản chép lại để chấm OCR và vùng chữ đã che | Ảnh gốc, mọi bản nén hoặc biến thể |
| URL | `url` hoặc `text` chứa địa chỉ | URL được rà, nhãn và ngày xác minh | Tên miền hoặc tenant theo Public Suffix List |
| QR | `qr_payload` và `text` tùy chọn | QR link/thanh toán, CRC và kết quả đối chiếu người nhận | Mã gốc và chiến dịch. Ảnh QR kiểm riêng bằng `/v1/qr/parse` |
| Ghi âm | `audio`, đường dẫn WAV PCM mono 16 bit, 16 kHz | Bản chép, người nói đã xin phép và nhãn loại âm thanh nếu đo phát hiện giả giọng | Người nói, cuộc gọi và bản cắt lại |
| Biên lai | `image`, `image_kind: "receipt"` | Vùng OCR và vùng chỉnh sửa có đối chiếu, ghi nguồn xác minh giao dịch nếu có | Ảnh gốc, biến thể nén và mẫu bố cục |

Harness gửi trường đầu vào theo hợp đồng ứng dụng. Bản chép, nhãn, vùng đáp án và thông tin người gán nhãn dùng để đánh giá tại QA. Báo cáo JSON ghi `synthetic_count` và `by_input` gồm số mẫu, p95 và lỗi. Ngưỡng p95 text/ảnh của MVP được giữ. Chốt ngưỡng riêng cho ghi âm, URL, QR và biên lai sau khi có mẫu đại diện. Gói smoke dùng thư mục `eval/generated/`, số liệu phát hành dùng tập đã khóa và ghi rõ tỷ lệ tổng hợp.

`eval/prepare_smoke.py` tạo cả `dataset.multimodal-smoke.jsonl` và `multimodal-smoke.manifest.json` với ví dụ tin nhắn, ảnh, URL, QR và biên lai. Sau khi cấu hình Whisper, dùng `--synthetic-audio` trỏ tới bản WAV tổng hợp của một câu hội thoại hợp lệ để thêm ca nghe vào smoke. Dùng tập riêng cho chất lượng ASR với âm thanh có sự đồng ý của người nói và bản chép được rà.

### Biên bản khóa tập dữ liệu

| Mục | QA ghi khi bàn giao |
|---|---|
| Định danh | Phiên bản dataset, ngày, người phụ trách và checksum từng tập |
| Nguồn | Nguồn hợp lệ, phạm vi cho phép và nơi lưu bản gốc |
| Phân bổ | Đếm theo kênh, nhãn, nhóm, nguồn và cờ `synthetic` |
| Tách tập | Train/dev/holdout, kiểm tra trùng theo đơn vị ở bảng trên, ghi cách xử lý ca mơ hồ |
| Duyệt | Người kiểm và ngày, phiên bản quy tắc gán nhãn, cách cập nhật mẫu bị rút |

## FraudURL-ML

Chuẩn bị hai tập JSONL do người gán nhãn xác minh, ngoài Git nếu có dữ liệu nhạy cảm. Mỗi dòng có trường `url`, `label` (`phishing` hoặc `benign`) và `verified: true`. Tập train và holdout tách theo tên miền đăng ký. Mỗi tập cần tối thiểu 10 tên miền khác nhau cho mỗi nhãn để chạy lệnh. Khi đo chất lượng, lấy thêm mẫu URL lành có tên giống thương hiệu và chiến dịch phishing theo thời gian.

```powershell
.\.venv\Scripts\python.exe -m pip install lightgbm==4.7.0
.\.venv\Scripts\python.exe eval/train_fraud_url.py eval/raw/fraud-url-train.jsonl eval/holdout.jsonl eval/generated/fraud-url-candidate
```

Lệnh lưu artifact LightGBM và `manifest.json` kèm recall, tỷ lệ báo nhầm, Brier score và mã SHA-256. Sau khi xem kết quả holdout, đặt `FRAUD_URL_MODEL_PATH` tới `fraud-url-v1.txt` để thử bên cạnh bộ luật. Giữ `manifest.json` cùng thư mục. Kích hoạt trong môi trường triển khai cần cài LightGBM tương ứng. [LightGBM Booster](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.Booster.html)
