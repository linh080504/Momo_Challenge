# Đánh giá MVP

- `dataset.example.jsonl` có 18 ví dụ tổng hợp. `prepare_smoke.py` tạo thêm 5 ảnh từ những ví dụ này để kiểm tra OCR. Tập sinh ra có các ca văn bản và ảnh trùng nội dung, phù hợp cho smoke test.
- QA đưa mẫu đã duyệt và ẩn danh vào `dataset.jsonl`, ảnh đã che thông tin vào `images/`, và lưu dữ liệu gốc ngoài Git. Dùng hướng dẫn gán nhãn ở [dataset-guide.md](../.claude/skills/eval-harness/dataset-guide.md).
- Tập chính thức gồm ít nhất 100 mẫu và 20 ảnh theo Product Brief. QA giữ riêng 20 mẫu holdout trong `holdout.jsonl` đến lúc chốt số liệu.
- Cổng chính thức dùng recall ≥ 0,90, báo nhầm ≤ 0,10, p95 văn bản ≤ 6 giây và p95 ảnh ≤ 12 giây. Ghi tỷ lệ mẫu tổng hợp cùng với kết quả.
- Harness ghi `last_run.json` sau mỗi lần chạy có báo cáo và cập nhật `latest.json` khi lượt gọi API đạt. Dùng `--out eval/generated/reports` cho mẫu smoke. Nếu chạy nhiều mẫu trên bản public, đăng nhập tài khoản thử và truyền tên biến token bằng `--token-env`.

## Bộ SMS tiếng Việt VSMS

Lấy `train.csv` và `test.csv` từ bản đã ghim vào `eval/generated/vsms`. Công cụ đối chiếu checksum, giữ tách biệt hai tập và lọc trùng. Chế độ `--offline-api` chạy `/v1/analyze` bằng TestClient và SQLite tạm. LLM, RDAP và Safe Browsing đều tắt. [Nguồn và giấy phép](../docs/DATA_SOURCES.md#vietnamese-quality-assured-sms-scam-dataset)

```powershell
$paypauseVsms = 'eval/generated/vsms'
$paypauseRevision = 'a90e2bd7e8df2376939658075ba8094dcee488ad'
New-Item -ItemType Directory -Force $paypauseVsms | Out-Null
foreach ($paypauseSplit in @('train', 'test')) {
  Invoke-WebRequest -UseBasicParsing -ErrorAction Stop `
    -Uri "https://huggingface.co/datasets/trannguyenthaituan/vietnamese_sms_dataset/resolve/$paypauseRevision/$paypauseSplit.csv" `
    -OutFile "$paypauseVsms/$paypauseSplit.csv"
}
.\.venv\Scripts\python.exe eval/tools/prepare_vsms.py $paypauseVsms "$paypauseVsms/clean"
.\.venv\Scripts\python.exe .claude/skills/eval-harness/scripts/run_eval.py --data "$paypauseVsms/clean/vsms_test.jsonl" --offline-api --tag vsms-offline --out "$paypauseVsms/holdout"
```

Chỉ dùng `vsms_train.jsonl` khi chỉnh luật. Chạy `vsms_test.jsonl` với cấu hình đã cố định. Chỉ số của bộ SMS nhị phân gộp spam và lừa đảo thành lớp dương. Nghiệm thu Product Brief còn có tập riêng cho nhiều kênh và nhãn thủ đoạn.

### Ứng viên SMS chạy CPU

Ứng viên dùng TF-IDF ký tự và hồi quy logistic. Script tách dev từ tập train, kiểm tra trùng với holdout, chọn ngưỡng trên dev và đo lại trên holdout. Artifact có cờ `benchmark_only`. Môi trường benchmark đã dùng Linux Python 3.12 với scikit-learn 1.9.1. [Tài liệu TF-IDF](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html) · [Tài liệu logistic](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html)

```bash
python -m pip install scikit-learn==1.9.1
python eval/tools/benchmark_sms.py eval/generated/vsms/clean/vsms_train.jsonl eval/generated/vsms/clean/vsms_test.jsonl eval/generated/mvp-completion/sms-candidate
```

### Manifest của lượt đo

Sau khi chạy harness, dùng cùng dataset và báo cáo `last_run.json` cho cả hai lệnh. Có thể thêm `--artifact <file>` cho trọng số được dùng trong lượt đo. Lệnh ghi mới yêu cầu một đường dẫn manifest chưa tồn tại.

```bash
python eval/tools/release_manifest.py record eval/generated/rehearsal-manifest.json --dataset eval/generated/dataset.multimodal-smoke.jsonl --report eval/generated/mvp-completion/staging/last_run.json
python eval/tools/release_manifest.py verify eval/generated/rehearsal-manifest.json --dataset eval/generated/dataset.multimodal-smoke.jsonl --report eval/generated/mvp-completion/staging/last_run.json
```

## Benchmark OCR tiếng Việt

`eval/tools/check_ocr.py` so Tesseract bản MVP (`vie+eng`, PSM 11), PP-OCRv5 Mobile với bộ đọc Latin và PP-OCRv6 Small trên CPU. Hai cấu hình Paddle giới hạn cạnh dài ở 1.280 pixel khi dò vùng chữ. Báo cáo ghi p95 phần OCR, số từ của bản chép được giữ, số tín hiệu trùng với bản chép và mức rủi ro khi chuyển chữ đã đọc vào bộ phân tích offline. Bản chép dùng để chấm có thể chỉ gồm phần nội dung liên quan. Tỷ lệ giữ từ đếm số lần xuất hiện của từ tham chiếu theo kiểu không xét thứ tự. Báo cáo chỉ lưu ID và số đo. [Tesseract PSM](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html#page-segmentation-method) · [PaddleOCR](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html)

Ví dụ trên Linux với Python 3.12, môi trường đã cài `apps/api/requirements.txt`, Tesseract và gói ngôn ngữ Việt. Môi trường thử Paddle cần thêm `libgl1` và `libglib2.0-0`. Preload lấy trọng số, sau đó có thể chạy lệnh benchmark với mạng tắt. Dùng `--engines tesseract` để kiểm tra OCR hiện tại mà không cần Paddle.

```bash
python -m pip install paddleocr==3.7.0 paddlepaddle==3.2.0
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True python eval/tools/check_ocr.py --preload --engines pp-ocrv5 pp-ocrv6-small
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True python eval/tools/check_ocr.py --dataset eval/dataset.jsonl --output eval/generated/ocr-dev-comparison.json
```

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

Phần huấn luyện bên dưới dành cho nghiên cứu và tái lập benchmark. Nghiệm thu MVP dùng URL Việt đã rà nhãn để đánh giá cổng tên miền đang chạy qua `/v1/analyze` và `/v1/qr/parse`. [Phạm vi FraudURL của MVP](../docs/STATUS.md#phạm-vi-fraudurl-của-mvp)

### Kiểm thử cổng URL của MVP

Chuẩn bị JSONL có `id`, `candidate`, `label` (`phishing` hoặc `benign`) và `source` (trang nguồn xác nhận). Có thể giữ dấu chấm dưới dạng `[.]` trong `candidate`. Script chỉ chuyển chuỗi cho API PayPause. Báo cáo lưu mã mẫu, mức rủi ro, mã HTTP và độ trễ theo ba kênh. Dùng tập dev nhỏ để rà trường hợp `uncertain` trước khi chạy tập độc lập. Test QR qua payload trong mục này. Ảnh QR đi qua bài kiểm thử API và trình duyệt riêng.

```powershell
.\.venv\Scripts\python.exe eval/tools/check_url_channels.py eval/generated/url-channel-dev.jsonl eval/generated/url-channel-dev.report.json
```

Chuẩn bị hai tập JSONL do người gán nhãn xác minh, ngoài Git nếu có dữ liệu nhạy cảm. Mỗi dòng có trường `url`, `label` (`phishing` hoặc `benign`) và `verified: true`. Tập train và holdout tách theo tên miền đăng ký. Mỗi tập cần tối thiểu 10 tên miền khác nhau cho mỗi nhãn để chạy lệnh. Khi đo chất lượng, lấy thêm mẫu URL lành có tên giống thương hiệu và chiến dịch phishing theo thời gian.

```powershell
.\.venv\Scripts\python.exe -m pip install lightgbm==4.7.0
.\.venv\Scripts\python.exe eval/train_fraud_url.py eval/raw/fraud-url-train.jsonl eval/holdout.jsonl eval/generated/fraud-url-candidate
```

Lệnh lưu artifact LightGBM và `manifest.json` kèm recall, tỷ lệ báo nhầm, Brier score và mã SHA-256. Sau khi xem kết quả holdout, đặt `FRAUD_URL_MODEL_PATH` tới `fraud-url-v1.txt` để thử bên cạnh bộ luật. Giữ `manifest.json` cùng thư mục. Kích hoạt trong môi trường triển khai cần cài LightGBM tương ứng. [LightGBM Booster](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.Booster.html)

### Benchmark FraudURL trên tập UCI

Tải archive PhiUSIIL của Prasad và Chandra vào `eval/generated/phiusiil/phiusiil.zip`. Giấy phép là CC BY 4.0. Script chỉ đọc cột URL và nhãn để tạo đặc trưng offline. Nó bỏ đường dẫn, tham số và thông tin đăng nhập khỏi bản dùng đánh giá. Chia theo tên miền đăng ký, lấy một mẫu mỗi miền, loại miền có nhãn mâu thuẫn và ghi checksum. [Nguồn PhiUSIIL tại UCI](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset)

```powershell
.\.venv\Scripts\python.exe -m pip install lightgbm==4.7.0 xgboost-cpu==3.4.1
.\.venv\Scripts\python.exe eval/tools/prepare_fraud_url.py eval/generated/phiusiil/phiusiil.zip eval/generated/phiusiil/splits-v1
.\.venv\Scripts\python.exe eval/train_fraud_url.py eval/generated/phiusiil/splits-v1/train.jsonl eval/generated/phiusiil/splits-v1/holdout.jsonl eval/generated/phiusiil/benchmark-v1 --dev eval/generated/phiusiil/splits-v1/dev.jsonl --uci-benchmark --compare-xgboost
```

Manifest model ghi kết quả tại ngưỡng mặc định và ngưỡng được chọn trên dev với giới hạn FPR 10%. Kết quả tại ngưỡng dev được đo lại trên holdout. Dùng benchmark này để so sánh thuật toán. Dữ liệu Việt Nam cần tập riêng đã được đội xác minh. API từ chối nạp artifact `benchmark_only`.
