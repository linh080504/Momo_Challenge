---
name: submission-pack
description: "Soạn và kiểm tra 4 thành phần bài nộp cuộc thi — PDF hướng dẫn 1 trang A4 (link + tài khoản test), README trong file zip mã nguồn (cách chạy, công nghệ, tài sản có sẵn, thư viện OSS, công cụ AI), slide ≤ 10 trang PDF, video ≤ 3 phút MP4. Chỉ chạy khi được gọi /submission-pack."
disable-model-invocation: true
argument-hint: "[guide | readme | slides | video | check]"
---

# Submission pack

Việc cần làm: `$ARGUMENTS` (trống → chạy `check`).

## Ràng buộc từ đề bài (không được vi phạm)

| Thành phần | Ràng buộc |
|---|---|
| Hướng dẫn sử dụng | Tối đa 1 trang A4, PDF, có link sản phẩm dùng được ngay, có tài khoản dùng thử |
| Mã nguồn | File .zip toàn bộ mã nguồn; README khai báo cách chạy, công nghệ, danh sách tài sản có sẵn, thư viện mã nguồn mở, công cụ AI đã dùng |
| Slide | Tối đa 10 trang, PDF, nêu rõ vấn đề và giải pháp; dùng cho chung kết, **không sửa được sau khi nộp** |
| Video | Tối đa 3 phút, MP4, quay sản phẩm đang chạy thật; phần quá 3 phút không được xem |

## guide → `submission/HUONG_DAN.md` rồi xuất PDF

Dùng `templates/user-guide-1page.md`. Sau khi xuất PDF, kiểm tra đúng 1 trang (ví dụ `pdfinfo file.pdf | grep Pages`). Thử mọi link và tài khoản trong file trên máy lạ.

## readme → `submission/README.md` (đặt ở gốc file zip)

Dùng `templates/README-template.md`. Liệt kê thư viện tự động: đọc `package.json`, `pyproject.toml`/`requirements.txt` để lấy tên + license. Mục "Công cụ AI" tách hai phần: AI chạy trong sản phẩm, và AI hỗ trợ phát triển (Claude Code, các subagent/skill trong `.claude/`).

## slides → `submission/SLIDES_OUTLINE.md`

Dùng `templates/slide-outline.md`. Mọi số liệu phải có nguồn (bối cảnh) hoặc lấy từ báo cáo eval mới nhất `eval/reports/latest.json` (kết quả). Không đưa số chưa đo.

## video → `submission/VIDEO_SCRIPT.md`

Dùng `templates/video-script.md`. Khoảnh khắc "wow" trước giây 50, tổng ≤ 2:55.

## check

Đi qua `templates/final-checklist.md`, với mỗi mục ghi PASS/FAIL kèm bằng chứng (lệnh đã chạy, kết quả). Ghi bảng kết quả vào `docs/STATUS.md`.
