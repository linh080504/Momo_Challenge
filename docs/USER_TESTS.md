# Thử nghiệm với người dùng thật (mục tiêu ≥ 10 người trước G2)

| #   | Ngày | Persona (tuổi, nghề) | Đầu vào họ dùng | Họ có hiểu kết quả? | Họ sẽ làm gì tiếp? | Câu nói nguyên văn (xin phép dùng) | Lỗi/khó khăn |
| --- | ---- | -------------------- | --------------- | ------------------- | ------------------ | ---------------------------------- | ------------ |

## Kịch bản nghiệm thu bản nâng cấp

Kịch bản dưới đây là kế hoạch. Ghi kết quả từng buổi vào bảng phía trên sau khi thử. Dùng dữ liệu tổng hợp hoặc dữ liệu đã ẩn danh, được phép sử dụng. Ghi loại đầu vào, hành động người tham gia chọn, thời gian và lỗi. [Phạm vi sản phẩm](PRODUCT_BRIEF.md#phạm-vi-phiên-bản-nâng-cấp-paypause-ai)

| Ca | Đầu vào hoặc thao tác | Quan sát và ghi kết quả |
|---|---|---|
| UT-01 · Tin nhắn | Một tin sinh hoạt và một tin thúc chuyển tiền hoặc xin mã xác thực. | Người tham gia hiểu dấu hiệu, chỉ được câu chữ liên quan và biết cách xác minh qua kênh chính thức. |
| UT-02 · Ảnh chụp | Ảnh màn hình tiếng Việt rõ chữ, ảnh mờ và ảnh sai định dạng. | Ghi tỷ lệ OCR đọc được, khả năng hiểu trạng thái chờ, thông báo lỗi và hành động sau kết quả. |
| UT-03 · URL | Tên miền chính thức, tên miền mô phỏng gần giống và tên miền có Unicode. | Người tham gia nhận biết tên miền đích và lý do cảnh báo. Khi nguồn tra cứu vắng mặt, kiểm tra họ hiểu giới hạn của kết quả. |
| UT-04 · QR | QR liên kết, VietQR đúng và VietQR có tài khoản khác tin nhắn hoặc CRC lỗi. | Người tham gia phân biệt QR mở web và QR chuyển khoản, đối chiếu ngân hàng/người nhận. Chức năng tạo lại QR đòi xác nhận người nhận và mức rủi ro phù hợp. |
| UT-05 · Ghi âm | Bản ghi có sự đồng ý của người nói, gồm lời bình thường, lời thúc chuyển tiền và đoạn có nhiễu. | Khi có Whisper thật, ghi lỗi phiên âm, thời gian và khả năng hiểu bằng chứng. Khi triển khai FraudVoice, đo riêng phát hiện giả mạo giọng. |
| UT-06 · Biên lai | Ảnh gốc, bản nén và mẫu có vùng thay đổi đã gán nhãn. | Người tham gia xem ảnh và vùng bằng chứng, hiểu rằng giao dịch cần xác minh qua lịch sử ngân hàng. Ghi lỗi vùng OCR và báo nhầm do nén. |
| UT-07 · Đồ thị và duyệt | Gửi nhiều báo cáo có thực thể trùng, xem đồ thị, kiểm tra bản nháp, duyệt hoặc bác bỏ. | Vai vận hành tra được nguồn và giải thích quan hệ. Cảnh báo web chỉ xuất hiện sau duyệt. Kiểm tra tài khoản người dùng không thể duyệt hoặc tải phản hồi vận hành. |
| UT-08 · Phản hồi và phiên bản | Một hồ sơ chờ duyệt, một hồ sơ bị bác, một hồ sơ đã duyệt và một phiên bản model ứng viên. | Chỉ hồ sơ đủ điều kiện xuất hiện trong phản hồi đã xác minh. QA truy lại được phiên bản dataset, model, prompt và kết quả holdout trước khi kích hoạt. |
| UT-09 · Dịch vụ gián đoạn | Mô phỏng Qwen, nguồn tra cứu hoặc ghi âm không khả dụng ở môi trường thử. | Với phân tích có thể tiếp tục bằng luật, ghi trạng thái hạn chế và cách người dùng xử lý. Với tệp cần bộ xử lý đang thiếu, ghi thông báo và hành động thay thế được hiểu. |

Giữ mục tiêu ít nhất **10 người dùng thử**. Đo riêng quy trình thủ công và `/ops` trên **5 chiến dịch, mỗi chiến dịch 8–10 báo cáo**, ghi thời gian và số quyết định đúng. Xác nhận quy trình với một người có kinh nghiệm vận hành hoặc CSKH. Số liệu kiểm thử tự động và mẫu tổng hợp lưu ở STATUS hay báo cáo eval. [Chỉ số thành công](PRODUCT_BRIEF.md#5-chỉ-số-thành-công) · [Trạng thái kiểm thử tự động](STATUS.md#2026-11-27--bản-nâng-cấp-chạy-local)

## Kiểm thử quyết định trước khi xác nhận

Dùng ảnh và giao dịch giả lập để so sánh thẻ chấm điểm hiện tại với màn hình `/truoc-khi-xac-nhan`. Đổi thứ tự hai giao diện giữa người tham gia và dùng hai bộ ca tương đương. Bắt đầu tính thời gian khi kết quả xuất hiện. Hỏi trước khi gợi ý **Nếu bấm xác nhận thì tiền đi đâu? Bạn sẽ làm gì tiếp?**

| Ca | Quan sát |
|---|---|
| Chờ hoàn tiền nhưng nhận VietQR chuyển khoản | Người dùng tự nhận ra tiền sẽ đi ra, chọn dừng hoặc xác minh qua kênh chính thức. |
| Thanh toán bình thường | Người dùng nhận ra đây là lệnh trả tiền, kiểm tra người nhận và số tiền. Ghi số ca bị gián đoạn vì cảnh báo. |
| Ảnh QR mờ hoặc chỉ có QR liên kết | Người dùng hiểu chưa xác định được giao dịch và biết chọn ảnh rõ hơn hoặc mở Trợ giúp. |

| Mã người thử | Ca và giao diện | Nhận định về chiều tiền | Hành động đầu tiên | Số giây | Gián đoạn ở ca hợp lệ |
|---|---|---|---|---|---|

Mục tiêu thử nghiệm ban đầu là ít nhất 8/10 người tự nhận ra tiền sẽ chuyển đi trong ca hoàn tiền giả và thời gian trung vị chọn cách xác minh tối đa 20 giây. Ghi số người hoàn thành và số kết quả từng ca trước khi so sánh hai giao diện.

Với ca QR liên kết đến hostname đã được chuyên viên duyệt, hỏi người thử **Vì sao bạn nên dừng lại? Bạn sẽ xác minh ở đâu?** Thử thêm ca hồ sơ còn chờ duyệt và bài viết cảnh báo có nhắc MoMo. Với vai chuyên viên, ghi thời gian từ lúc nhận ứng viên CT đến lúc xem đủ bằng chứng và quyết định. Dùng tình huống giả lập trong bàn giao để giữ điều kiện thử nhất quán. [Kịch bản vận hành](MVP_HANDOFF.md#demo-phát-hiện-sớm-website-mạo-danh-momo)
