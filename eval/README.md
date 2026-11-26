# Đánh giá MVP

- `dataset.example.jsonl` có 18 ví dụ tổng hợp. `prepare_smoke.py` tạo thêm 5 ảnh từ những ví dụ này để kiểm tra OCR. Tập sinh ra có các ca văn bản và ảnh trùng nội dung, phù hợp cho smoke test.
- QA đưa mẫu đã duyệt và ẩn danh vào `dataset.jsonl`, ảnh đã che thông tin vào `images/`, và lưu dữ liệu gốc ngoài Git. Dùng hướng dẫn gán nhãn ở [dataset-guide.md](../.claude/skills/eval-harness/dataset-guide.md).
- Tập chính thức gồm ít nhất 100 mẫu và 20 ảnh theo Product Brief. QA giữ riêng 20 mẫu holdout trong `holdout.jsonl` đến lúc chốt số liệu.
- Cổng chính thức dùng recall ≥ 0,90, báo nhầm ≤ 0,10, p95 văn bản ≤ 6 giây và p95 ảnh ≤ 12 giây. Ghi tỷ lệ mẫu tổng hợp cùng với kết quả.
- Harness ghi `last_run.json` sau mỗi lần chạy có báo cáo và cập nhật `latest.json` khi lượt gọi API đạt. Dùng `--out eval/generated/reports` cho mẫu smoke. Nếu chạy nhiều mẫu trên bản public, đăng nhập tài khoản thử và truyền tên biến token bằng `--token-env`.
