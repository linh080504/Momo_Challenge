---
name: daily-standup
description: "Tổng hợp standup hằng ngày cho PM — đọc commit 24 giờ qua, trạng thái kế hoạch, báo cáo eval mới nhất; so với việc của ngày trong docs/PLAN.md; ghi nhật ký vào docs/STATUS.md và nêu việc bị trễ, rủi ro, quyết định cần chốt. Chỉ chạy khi được gọi /daily-standup."
disable-model-invocation: true
argument-hint: "[ngày-thứ-mấy, ví dụ 5]"
allowed-tools: Bash(git log *)
---

# Daily standup — ngày $ARGUMENTS

## Commit 24 giờ qua

!`git log --since="24 hours ago" --no-merges --pretty=format:"%h %an: %s"`

## Việc cần làm

1. Đọc mục của ngày $ARGUMENTS trong `docs/PLAN.md` và 40 dòng cuối `docs/STATUS.md`.
2. Đọc báo cáo eval mới nhất trong `eval/reports/` (nếu có).
3. So sánh: việc nào trong kế hoạch đã xong (có commit/bằng chứng), việc nào chưa.
4. Viết thêm vào cuối `docs/STATUS.md` đúng khuôn dưới đây (không sửa các ngày trước):

```markdown
## Ngày N — YYYY-MM-DD
- Đã xong: ... (kèm commit/link bằng chứng)
- Chưa xong / trễ: ... → ai xử lý, hạn mới
- Chỉ số: recall __, báo nhầm __, p95 __s (eval tag __) | uptime __
- Rủi ro mới: ...
- Cần PM quyết: ...
- Việc ngày mai: ...
```

5. Nếu ngày hôm nay là ngày có cổng (G0 ngày 1, G1 ngày 7, G2 ngày 10, G3 ngày 13), nhắc chạy `/gate-check`.
6. Trả lời ngắn gọn cho PM: 3 dòng tình hình + danh sách việc cần quyết.
