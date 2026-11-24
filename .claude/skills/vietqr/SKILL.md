---
name: vietqr
description: "Đọc, kiểm tra và tạo mã VietQR (chuẩn EMVCo/NAPAS) — lấy BIN ngân hàng, số tài khoản, số tiền, nội dung; phát hiện QR bị sửa (sai CRC); tạo \"QR sạch\" đúng người nhận. Dùng khi xử lý ảnh/chuỗi QR người dùng gửi, khi xây tính năng tạo QR thanh toán, hoặc khi kiểm tra QR có khớp người nhận được nhắc trong tin nhắn."
allowed-tools: Bash(python3 .claude/skills/vietqr/scripts/vietqr.py *)
---

# VietQR

Script: `scripts/vietqr.py` (thư viện chuẩn; đọc ảnh cần `opencv-python-headless`).

```bash
python3 .claude/skills/vietqr/scripts/vietqr.py parse "<chuỗi QR>"
python3 .claude/skills/vietqr/scripts/vietqr.py build --bin 970436 --account 0123456789 --amount 50000 --note "TKC 123"
python3 .claude/skills/vietqr/scripts/vietqr.py image path/to/qr.png
```

## Cấu trúc cần nhớ

- TLV: 2 số tag + 2 số độ dài + giá trị. Tag 00 = "01", tag 01 = "11" (tĩnh) / "12" (động).
- Tag 38 = thông tin người nhận: 00 GUID `A000000727` (NAPAS), 01 = {00 BIN 6 số, 01 số tài khoản/thẻ}, 02 `QRIBFTTA` (tài khoản) hoặc `QRIBFTTC` (thẻ).
- 53 = `704` (VND), 54 = số tiền, 58 = `VN`, 62.08 = nội dung chuyển khoản, 63 = CRC-16/CCITT-FALSE tính trên toàn chuỗi kể cả `6304`.

## Dùng trong sản phẩm

- **Kiểm tra QR người dùng gửi**: `valid_crc=false` → cộng điểm rủi ro (QR bị ghép tay). So `account`, `bank_bin` với số tài khoản trong tin nhắn và với danh sách đen. Tin nhắn nói "chuyển cho Công an quận" mà QR là tài khoản cá nhân → dấu hiệu G1.
- **QR sạch**: chỉ tạo khi rủi ro `low` và người dùng tự xác nhận người nhận. Hiển thị rõ tên ngân hàng, 4 số cuối tài khoản, số tiền trước khi hiện QR.
- **Ảnh QR từ BGK**: hiển thị ngay các trường đã giải mã để BGK thấy hệ thống "đọc thật".

## Lưu ý

- Bảng `BANK_BINS` trong script chỉ có 10 ngân hàng. Khi khởi động backend, tải danh sách đầy đủ từ `https://api.vietqr.io/v2/banks` và cache.
- Không dùng QR để tự chuyển tiền. Sản phẩm chỉ tạo mã để người dùng quét trong app ngân hàng của họ.
- Test: `python3 tests/test_kit_scripts.py` (có kiểm tra CRC chuẩn "123456789" → 29B1 và round-trip).
