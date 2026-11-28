# Bàn giao PayPause AI

MVP hiện dùng Qwen4-Max, bộ quy tắc, OCR cục bộ, Whisper có sẵn và các nguồn đối chiếu. Phản hồi do chuyên viên gán nhãn được dùng để kiểm tra chất lượng và rà quy tắc. Huấn luyện, fine-tune và kích hoạt model thử nghiệm nằm ngoài phạm vi bản bàn giao này.

## Phần người dùng

| Đầu vào | Điểm vào | Nội dung cần nhìn thấy |
| --- | --- | --- |
| Tin nhắn | **Website → Tin nhắn** | Ngữ cảnh, dấu hiệu trong lời nhắn, mức rủi ro và câu hỏi kiểm chứng theo tình huống. |
| Ảnh chụp | **Website → Ảnh chụp** | **Kiểm tra ngay** gửi ảnh đã chọn đến QwenCloud để đọc chữ và tiếp tục phân tích. Hệ thống dùng OCR cục bộ khi Qwen chưa đọc được ảnh. |
| Website | **Website** | Nhận định từng đoạn của Qwen, ảnh chụp cuộn được, thời gian kiểm tra và kết quả từng nguồn. |
| Mã QR | **Website → Mã QR** hoặc **VietQR** | Loại QR, tên miền hoặc ngân hàng, tài khoản đã che và tình trạng xác minh. |
| Ghi âm | **Website → Ghi âm** | Phiên âm bằng Whisper. Có thể dán lời thoại và bấm kiểm tra ngay trong cùng tab khi cần. |
| Biên lai | **Website → Biên lai** | Ảnh gốc, vùng OCR, sai khác nén nếu có và trạng thái giao dịch cần xác minh. |

**Hỏi người thân** tạo liên kết tóm tắt có hiệu lực 24 giờ. **Báo cáo** đưa tín hiệu đã che vào hồ sơ vận hành sau khi người dùng đồng ý.

## Phần vận hành

1. Mở **Vận hành** bằng tài khoản ops. Tổng quan hiển thị số báo cáo và quyết định trong 24 giờ, cùng số hồ sơ đang chờ hoặc đã duyệt. Mục **Cấu hình hệ thống** cho biết phiên bản API, prompt, kho tri thức và các dịch vụ đã bật. Trạng thái cấu hình cần được kiểm chứng thêm bằng một lượt thử thực tế.
2. Mở chiến dịch và chọn nút trên đồ thị để xem các thực thể đã ẩn danh. Cạnh giữa thực thể và đầu vào ghi số báo cáo có cả hai dữ kiện, kèm thời điểm gần nhất trong các báo cáo đã đọc.
3. Mở **Gán nhãn báo cáo**, chọn *Lừa đảo*, *Hợp lệ*, *Cần xác minh* hoặc *Rút nhãn*, rồi xem lịch sử. Lưu nhãn và duyệt chiến dịch là hai thao tác độc lập. Với hồ sơ chờ duyệt có ít nhất hai báo cáo, chuyên viên có thể tách một báo cáo và mang theo lịch sử nhãn. Nếu bản ghi đã đổi ở phiên khác, tải lại trước khi sửa tiếp.
4. Mở **Cảnh báo theo kênh**. Cảnh báo web xuất hiện khi một lần phân tích khớp thực thể của chiến dịch đã duyệt. Mẫu in-app, email, SMS và nội bộ có thể xem trong hồ sơ. Trạng thái biên lai là `unverified` đến khi có nguồn giao dịch được cấp quyền.
5. API `GET /v1/ops/feedback/samples` xuất mẫu tín hiệu có nhãn mới nhất là `scam` hoặc `legit`, dùng `next_cursor` với tham số `after` để lấy trang tiếp. `group_id` là chiến dịch hiện tại, dùng để giữ cùng chiến dịch trong một tập. Bản xuất gồm mã mẫu, nhóm, nhãn, phiên bản nhãn và tín hiệu. Khi người dùng xóa báo cáo, lịch sử nhãn tương ứng cũng được xóa. Việc dùng nội dung gốc cho huấn luyện cần theo quyền riêng của dataset.

## Đo chất lượng và quay lui

- Chạy `python eval/tools/rehearse_ops.py --out eval/generated/ops-rehearsal.json` để thử API với 5 chiến dịch tổng hợp, mỗi chiến dịch 8 báo cáo. Phép đo này ghi thời gian API của từng lượt gán nhãn và duyệt.
- Dùng `eval/tools/release_manifest.py record` và `verify` với cùng dataset, báo cáo và trọng số. Dùng `--artifact` lặp lại khi có nhiều tệp. Manifest ghi checksum, phiên bản Git, model, prompt và kết quả từng cổng. Quy trình giữ bản phát hành trước để quay lui. [Hướng dẫn môi trường và quay lui](../infra/deploy/README.md)
- Các thẻ hướng dẫn G1–G5 và Black Friday lấy từ nội dung đã rà. API trả mã, phiên bản và liên kết nguồn. Chủ sở hữu nội dung là nhóm QA sản phẩm. [Nguyên tắc của Vietcombank](https://www.vietcombank.com.vn/vi-VN/KHCN/Danh-sach-nguyen-tac-GDAT/) · [Hướng dẫn MoMo](https://www.momo.vn/hoi-dap/nhan-biet-dau-hieu-lua-dao-nhu-the-nao) · [Hướng dẫn mua sắm dịp lễ của FTC](https://consumer.ftc.gov/consumer-alerts/2025/11/how-avoid-online-shopping-scam-holiday-season)

## Đối chiếu 15 bước

| Bước | Đã có trong MVP | Điều kiện nghiệm thu còn mở |
| --- | --- | --- |
| 1 · Hợp đồng | Hai hành trình, sáu kênh, phân quyền và schema API | |
| 2 · Môi trường | SQLite, Compose PostgreSQL, migration và harness | Xác nhận cấu hình môi trường từ xa |
| 3 · Bảo mật | Chuẩn hóa URL, đối chiếu nguồn, xác thực và che dữ liệu | Safe Browsing thật và kiểm tra egress ở môi trường đích |
| 4 · Dữ liệu và nội dung | Mẫu tổng hợp, bộ SMS độc lập, bộ lọc trùng và thẻ tri thức có nguồn | Khóa holdout đại diện đa kênh, có quyền sử dụng |
| 5 · Sáu đầu vào | Web và API cho tin nhắn, ảnh, website, QR, ghi âm và biên lai | |
| 6 · Nhận diện chuyên biệt | Dùng các quy tắc theo ngữ cảnh, kiểm tra URL và nguồn đối chiếu | Kiểm chứng độ phủ trên holdout theo từng tác vụ |
| 7 · Kiểm định nghe nhìn | OCR, Whisper và vùng bằng chứng biên lai | Dữ liệu ASR giọng vùng miền, ảnh nén và vùng chỉnh sửa có nhãn |
| 8 · Định tuyến và truy xuất | Fast/Deep Path, Qwen4-Max, thẻ G1–G5 và câu hỏi theo tình huống | Đo tỷ lệ cảnh báo nhầm, độ trễ và chi phí trên tập đại diện |
| 9 · Đồ thị | Gom và tách báo cáo, xem quan hệ theo báo cáo, kênh và thời điểm | Đo gộp/tách nhầm và hiệu chuẩn có holdout |
| 10 · Workspace | Supervisor, sáu agent, tổng quan 24 giờ, bộ lọc và duyệt theo phiên bản | Đo hiệu quả thao tác với chuyên viên thật |
| 11 · Cảnh báo | Cảnh báo web sau duyệt, mẫu nội dung bốn kênh và trạng thái `unverified` | Quyền đối tác gửi cảnh báo và xác minh giao dịch |
| 12 · Phản hồi | Nhãn từng báo cáo, lịch sử, rút nhãn và xuất tín hiệu có phiên bản | Nhãn vùng/chữ/lời nói trên tập dữ liệu được phép |
| 13 · Phiên bản | Manifest checksum, báo cáo cổng chất lượng, endpoint cấu hình | Thử chuyển phiên bản ở môi trường đích |
| 14 · Nghiệm thu | Diễn tập API 5 chiến dịch, 40 báo cáo và kịch bản 9 ca thử | Holdout đạt ngưỡng và ít nhất 10 người dùng thực hiện thử |
| 15 · Triển khai | Runbook, Docker, migration, `/health` và `/ready` | URL phát hành, người trực và xác minh giám sát trên môi trường đích |

[Kế hoạch chi tiết](PLAN.md#kế-hoạch-xây-dựng-từng-bước) · [Kịch bản người dùng thử](USER_TESTS.md#kịch-bản-nghiệm-thu-bản-nâng-cấp) · [Tiến độ và số đo](STATUS.md)
