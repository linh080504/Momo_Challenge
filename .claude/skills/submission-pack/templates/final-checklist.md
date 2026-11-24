# Checklist cuối (ghi PASS/FAIL + bằng chứng)

## Sản phẩm
- [ ] Link public mở được trên máy lạ, mạng 4G, < 5 giây (ghi thời gian đo)
- [ ] 2 tài khoản test đăng nhập được, dữ liệu demo đã nạp
- [ ] `smoke_test.sh` ĐẠT trên URL public
- [ ] BGK dùng được với input của chính họ (thử 3 tin nhắn thật chưa có trong eval)
- [ ] Có người trực + quy trình rollback

## PDF hướng dẫn
- [ ] Đúng 1 trang A4 (`pdfinfo`), có link, QR, tài khoản, cách thử bàn làm việc

## Mã nguồn
- [ ] Zip chứa toàn bộ mã nguồn, giải nén và chạy được theo README trên máy sạch
- [ ] README có đủ: cách chạy, công nghệ, tài sản có sẵn, thư viện OSS, công cụ AI
- [ ] Không lộ secret (quét bằng gitleaks hoặc `git grep -nE "(sk-|api[_-]?key|secret)"`)
- [ ] Không có `node_modules`, `.venv`, dữ liệu chưa ẩn danh

## Slide
- [ ] ≤ 10 trang, PDF, nêu rõ vấn đề và giải pháp
- [ ] Mọi số liệu có nguồn hoặc khớp `eval/reports/latest.json`

## Video
- [ ] ≤ 3:00, MP4, quay sản phẩm chạy thật (`ffprobe`)

## Bám đề
- [ ] Nói được trong 1 câu: chủ đề, người dùng, AI làm gì
- [ ] Có lớp đội ngũ vận hành (Future Workspace), con người duyệt bước rủi ro
