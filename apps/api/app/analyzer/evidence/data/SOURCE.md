# Nguồn dữ liệu bằng chứng

## `vn-badsite-filter-domains.txt`

- Dự án: [malware-filter/vn-badsite-filter](https://gitlab.com/malware-filter/vn-badsite-filter), tác giả curben. Giấy phép: **MIT** (mã), **CC0 1.0** (dữ liệu).
- Nguồn gốc dữ liệu: `api.chongluadao.vn` (Chống Lừa Đảo), CC0 theo README của dự án.
- File tải: `https://malware-filter.gitlab.io/vn-badsite-filter/vn-badsite-filter-domains.txt`. Bản dự phòng: `https://vn-badsite-filter.pages.dev/vn-badsite-filter-domains.txt`.
  - Lưu ý: đường dẫn `.../malware-filter/vn-badsite-filter-domains.txt` trả **404**.
- Bản chụp: tải ngày 2026-11-26, nguồn cập nhật lần cuối **2025-04-11**, gồm 16.843 tên miền. sha256 của file gốc nằm ở đầu file.
- **Hạn chế:** README ghi "Daily update of this blocklist has been stopped due to deprecation of upstream source". Danh sách đã đóng băng, có lẫn trang cờ bạc. Vì vậy chỉ dùng khi **trúng**: không có trong danh sách KHÔNG có nghĩa là an toàn.
- Đây là danh sách **bên thứ ba, chưa qua chuyên viên duyệt**. Trọng số thấp hơn "danh sách đen ĐÃ DUYỆT" (xem `scoring.py`). Không tự đưa thực thể nào từ đây vào danh sách đen nội bộ.
- Làm mới: `python -m app.analyzer.evidence.refresh_blacklist` (chạy trong `apps/api`).
