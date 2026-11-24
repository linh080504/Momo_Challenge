---
name: eval-harness
description: "Xây, mở rộng và chạy bộ đánh giá (eval) cho analyzer lừa đảo — tập mẫu JSONL có nhãn, chỉ số recall/báo nhầm/độ trễ, cổng chất lượng chặn merge khi điểm giảm. Dùng sau mỗi lần sửa prompt, đổi model, sửa luật chấm điểm, trước demo và trước khi chốt số liệu cho slide."
argument-hint: "[baseline | endpoint-url] [tag]"
allowed-tools: Bash(python3 .claude/skills/eval-harness/scripts/run_eval.py *)
---

# Eval harness

Nguyên tắc (theo Anthropic "Demystifying evals for AI agents"): định nghĩa "thành công" trước khi tối ưu, lấy mẫu từ lỗi thật, chấm theo kết quả chứ không ép từng bước, và giữ eval hồi quy để sửa chỗ này không làm hỏng chỗ khác.

## Chạy

```bash
# Mốc "không có AI" (bộ lọc từ khóa) — dùng cho bảng so sánh trên slide
python3 .claude/skills/eval-harness/scripts/run_eval.py --data eval/dataset.jsonl --baseline --tag baseline

# API thật, so với lần đạt gần nhất
python3 .claude/skills/eval-harness/scripts/run_eval.py --data eval/dataset.jsonl \
  --endpoint "$ANALYZER_URL/v1/analyze" --tag <ten-thay-doi> --compare eval/reports/latest.json
```

Nếu người dùng gọi `/eval-harness $ARGUMENTS`: tham số 1 là `baseline` hoặc URL endpoint, tham số 2 là tag.

Cổng mặc định: recall lừa đảo ≥ 0.90, tỷ lệ báo nhầm ≤ 0.10, p95 văn bản ≤ 6 giây (`--max-p95-text`), p95 ảnh ≤ 12 giây (`--max-p95-image`), không lỗi gọi API, recall không giảm quá 0.02 so với `latest.json`. Cổng p95 của một loại chỉ chấm khi tập có mẫu loại đó; báo cáo ghi rõ khi không có mẫu ảnh. Script trả exit code 1 nếu chưa đạt và chỉ ghi đè `latest.json` khi đạt.

Mẫu có trường `image` được gửi dưới dạng `image_base64` + `image_mime` (hợp đồng ở `scam-analyzer/SKILL.md`). `latest.json` có `p95_text`, `p95_image`, `n_text`, `n_image`; từng mẫu trong báo cáo có `input_type`. Ở chế độ `--baseline`, mẫu ảnh tính là "không đọc được" (`low`) nên recall baseline sẽ thấp hơn khi tập có ảnh — đó là mốc đúng cho bảng so sánh.

## Sau khi chạy

1. Đọc báo cáo `.md` mới nhất trong `eval/reports/`.
2. Với từng mẫu bỏ sót / báo nhầm: mở mẫu, đoán nguyên nhân (thiếu kịch bản trong taxonomy? luật chấm sai? prompt mơ hồ? OCR đọc sai?).
3. Đề xuất sửa nhỏ nhất, chạy lại. Không sửa nhãn dữ liệu chỉ để điểm đẹp; nếu nghi nhãn sai, ghi vào `docs/DECISIONS.md` và hỏi PM.
4. Báo kết quả bằng bằng chứng: dán bảng chỉ số và danh sách id sai, không chỉ nói "đã tốt hơn".

## Dữ liệu

- Định dạng, cách thu thập, phân bổ 100 mẫu, ẩn danh: xem `dataset-guide.md`.
- `eval/dataset.example.jsonl` có 18 mẫu TỔNG HỢP để chạy thử; không dùng để báo cáo số liệu.
- Tập thật: `eval/dataset.jsonl`. Giữ thêm `eval/holdout.jsonl` (20% mẫu) không ai được nhìn khi sửa prompt; chỉ chạy trước khi chốt slide.
