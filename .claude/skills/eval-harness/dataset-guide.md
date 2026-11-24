# Hướng dẫn xây bộ dữ liệu eval (mục tiêu ≥ 100 mẫu trong 5 ngày)

## Định dạng mỗi dòng (JSONL)

Mẫu văn bản:

```json
{"id": "s042", "text": "...", "label": "scam", "group": "G1", "channel": "zalo",
 "tags": ["hard_positive"], "synthetic": false, "source": "thanh-vien-A"}
```

Mẫu ảnh (thêm trường `image`):

```json
{"id": "s043", "text": "", "label": "scam", "group": "G5", "channel": "zalo",
 "tags": ["image"], "synthetic": false, "source": "thanh-vien-B",
 "image": "eval/images/s043.png", "transcript": "chép lại chữ trong ảnh, chỉ để người duyệt nhãn đọc"}
```

- `label`: `scam` | `legit`. `group`: G1–G5 theo taxonomy (null nếu legit).
- `tags`: `hard_positive` (lừa đảo khó nhận ra), `hard_negative` (tin thật dễ bị báo nhầm: OTP ngân hàng, shipper, khuyến mãi thật), `injection` (có câu ra lệnh cho AI), `image`, `audio`, `qr`.
- `synthetic: true` nếu do đội tự viết. Báo cáo trên slide phải ghi tỷ lệ mẫu tổng hợp.

### Trường `image` và cách `run_eval.py` gửi mẫu

| | Mẫu văn bản (không có `image`) | Mẫu ảnh (có `image`) |
|---|---|---|
| `input_type` trong báo cáo | `text` | `image` |
| Thân POST gửi lên `/v1/analyze` | `{"text": "..."}` | `{"text": "<text hoặc \"\">", "image_base64": "...", "image_mime": "image/png"\|"image/jpeg"}` |
| Cổng p95 | `--max-p95-text` (mặc định 6 giây) | `--max-p95-image` (mặc định 12 giây) |
| Chế độ `--baseline` | chấm bằng từ khóa | tính là "không đọc được" → `low` (kể cả khi có `text`) |

- `image`: đường dẫn file PNG hoặc JPEG, tính từ thư mục chạy lệnh (thường là gốc repo), ví dụ `eval/images/s043.png`. Ảnh tối đa **5 MB**. Loại đầu vào do trường `image` quyết định, không phải tag `image`: nhớ điền đủ cả hai.
- `image_mime` do script đọc từ byte đầu của file, không theo đuôi file. File không phải PNG/JPEG, quá 5 MB hoặc không đọc được → mẫu đó tính là **lỗi** (cổng "không có lỗi gọi API" sẽ rớt), không bao giờ tính là "an toàn".
- **`text` của mẫu ảnh để rỗng** (hoặc bỏ trường). Chỉ điền khi tình huống thật có chữ người dùng gõ kèm ảnh. Đừng chép nội dung ảnh vào `text`: eval sẽ gửi luôn đáp án cho analyzer và không còn đo được khả năng đọc ảnh.
- Muốn lưu bản chép lại nội dung ảnh để hai người duyệt nhãn đối chiếu thì để trong `transcript`; `run_eval.py` không gửi trường này.
- Tập phải có ≥ 20 mẫu ảnh thì cổng p95 ảnh mới có ý nghĩa; không có mẫu ảnh nào thì báo cáo ghi rõ "cổng p95 ảnh không được đánh giá".

## Phân bổ gợi ý cho 100 mẫu

| Loại | Số mẫu |
|---|---|
| Lừa đảo G1–G5 (mỗi nhóm ≥ 10) | 60 |
| Tin hợp lệ thường | 20 |
| Tin hợp lệ dễ nhầm (hard_negative) | 15 |
| Prompt injection | 5 |

Ít nhất 20 mẫu là ảnh chụp màn hình thật (đã che thông tin), vì BGK sẽ thử bằng ảnh.

## Nguồn mẫu

1. Tin lừa đảo thành viên, người thân đã nhận (xin phép, che tên, số điện thoại, số tài khoản).
2. Cảnh báo kèm ảnh minh họa của công an, ngân hàng, ví điện tử, báo chí — chép lại nội dung, ghi nguồn.
3. Tin hợp lệ: SMS ngân hàng, ví, sàn TMĐT, shipper, tin nhắn gia đình — đây là phần hay bị thiếu.
4. Mẫu tổng hợp: chỉ để lấp nhóm còn thiếu; người khác trong đội duyệt lại cho giống thật.

## Ẩn danh trước khi lưu

- Chạy `python3 .claude/skills/pii-guard/scripts/pii_mask.py` rồi thay token bằng giá trị giả nhất quán.
- Ảnh: che bằng ô đen, không làm mờ (làm mờ có thể khôi phục). Chỉ lưu ảnh đã che vào `eval/images/`; ảnh gốc để ngoài repo.
- Không commit dữ liệu chưa ẩn danh. Hook `protect-files.sh` chặn ghi vào `eval/raw/`.

## Gán nhãn

- Hai người gán độc lập 20 mẫu đầu, so sánh; lệch thì thống nhất quy tắc và ghi vào file này.
- Nghi ngờ → tag `ambiguous`, không đưa vào tập chấm điểm chính.
