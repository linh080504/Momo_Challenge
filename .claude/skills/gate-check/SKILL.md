---
name: gate-check
description: "Kiểm tra cổng kiểm soát G0–G3 của kế hoạch 14 ngày bằng bằng chứng thật (file tồn tại, eval chạy lại, smoke test trên URL public, checklist bài nộp) và ra kết luận ĐẠT/CHƯA ĐẠT. Chỉ chạy khi được gọi /gate-check G0|G1|G2|G3."
disable-model-invocation: true
argument-hint: "[G0 | G1 | G2 | G3]"
context: fork
agent: general-purpose
background: false
---

# Gate check $ARGUMENTS

Bạn là người kiểm tra độc lập: KHÔNG tin lời tự báo cáo, chỉ tin bằng chứng chạy được. Với mỗi tiêu chí của cổng $ARGUMENTS, chạy lệnh hoặc mở file để kiểm, ghi PASS/FAIL + bằng chứng. Thiếu bằng chứng = FAIL.

## G0 — cuối ngày 1: chốt đề
- `docs/PRODUCT_BRIEF.md` đủ: vấn đề, persona, luồng chính, danh sách Must, chỉ số, ngoài phạm vi
- `.claude/skills/scam-analyzer/taxonomy.md` đã đối chiếu danh sách 25 kịch bản (hoặc ghi rõ chưa tìm được)
- Repo, CI, tài khoản dịch vụ đã tạo; `.env.example` có đủ biến
- ≥ 50 mẫu dữ liệu đầu tiên (đã ẩn danh) trong `eval/`

## G1 — ngày 7: lõi chạy được
- URL public mở được; `bash .claude/skills/deploy-runbook/scripts/smoke_test.sh <API_URL>` ĐẠT
- `eval/dataset.jsonl` ≥ 100 mẫu; chạy eval với endpoint thật, ghi số đo lần 1 (chưa cần đạt cổng)
- Bàn làm việc: báo cáo từ người dùng xuất hiện trong hàng chờ; gom được ít nhất 1 chiến dịch; nút Duyệt làm thực thể vào danh sách đen
- Một người ngoài đội dùng thử không cần hướng dẫn (ghi tên + nhận xét)

## G2 — ngày 10: feature freeze
- Eval ĐẠT cổng (recall ≥ 0.90, báo nhầm ≤ 0.10, **p95 văn bản ≤ 6s, ảnh ≤ 12s** — đọc `p95_text`, `p95_image` trong `eval/reports/latest.json`)
- Tối đa 2 mục Should đã xong và chạy trên bản public
- ≥ 10 người dùng thật đã thử; nhận xét lưu ở `docs/USER_TESTS.md`
- Không còn lỗi mức nghiêm trọng mở trong danh sách việc

## G3 — ngày 13: nộp bài
- Chạy toàn bộ `.claude/skills/submission-pack/templates/final-checklist.md`
- Holdout eval (`eval/holdout.jsonl`) đã chạy; số trên slide khớp báo cáo
- Đã nộp, có ảnh chụp xác nhận; lịch trực đến hết vòng chấm

## Đầu ra

Bảng `| Tiêu chí | PASS/FAIL | Bằng chứng |`, kết luận ĐẠT/CHƯA ĐẠT, và với mỗi FAIL: việc cụ thể cần làm + người phụ trách gợi ý. Ghi kết quả vào cuối `docs/STATUS.md`.
