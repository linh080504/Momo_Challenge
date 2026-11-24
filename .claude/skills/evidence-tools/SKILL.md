---
name: evidence-tools
description: "Các công cụ tra bằng chứng cho agent phân tích lừa đảo — kiểm tra tên miền nhái/lạ, tuổi tên miền (RDAP), Google Safe Browsing, danh sách đen nội bộ đã duyệt, danh sách trắng ngân hàng/cơ quan. Dùng khi xây hoặc sửa bước \"tra bằng chứng\" (apps/api/app/evidence), khi thêm nguồn dữ liệu mới, hoặc khi cần kiểm tra nhanh một link/tên miền."
allowed-tools: Bash(python3 .claude/skills/evidence-tools/scripts/domain_check.py *)
---

# Evidence tools

Mục tiêu: mỗi kết luận của AI đi kèm bằng chứng kiểm tra được. Code thu bằng chứng, LLM chỉ diễn giải.

## Công cụ có sẵn

```bash
python3 .claude/skills/evidence-tools/scripts/domain_check.py "https://vietcombank-xacminh.top/login"
python3 .claude/skills/evidence-tools/scripts/domain_check.py --rdap example.com   # thêm tuổi tên miền (cần mạng)
```

Trả JSON: `score` 0–100, `level` low/medium/high, danh sách `signals` (official, brand_in_unofficial, lookalike, punycode, risky_tld, ip_url, shortener, gov_claim, new_domain...).

## Công cụ cần xây trong backend (`apps/api/app/evidence/`)

| Tool | Đầu vào | Cách làm | Ghi chú |
|---|---|---|---|
| `check_domain` | URL | port logic `domain_check.py` | danh sách trắng để trong DB, admin sửa được |
| `safe_browsing` | URL | Google Safe Browsing Lookup API v4, `threatMatches:find` | cần API key; cache 24h; xem `reference.md` |
| `domain_age` | tên miền | RDAP qua `https://rdap.org/domain/<d>` | đuôi `.vn` thường không có RDAP → trả `null`, không coi là an toàn |
| `blacklist_lookup` | hash STK/SĐT/URL | bảng `entities` (chỉ hash) + trạng thái `approved` | chỉ thực thể đã được chuyên viên duyệt mới tính điểm cao |
| `report_count` | hash | đếm báo cáo chưa duyệt | hiển thị "đã có N người báo cáo", điểm thấp hơn |
| `expand_short_url` | link rút gọn | HEAD request phía server, không theo quá 3 lần chuyển hướng, timeout 3s | chạy server, không bao giờ trên máy người dùng |

Agent (LLM) gọi các tool này qua function calling, hoặc backend gọi song song rồi đưa kết quả vào prompt (nhanh hơn, dễ kiểm soát hơn — khuyến nghị cho MVP).

## An toàn

- Không tải nội dung trang lạ về server nếu không cần; nếu cần chụp ảnh trang, dùng môi trường cách ly và timeout ngắn.
- Không gọi API bên thứ ba bằng dữ liệu cá nhân chưa ẩn danh; chỉ gửi URL/tên miền.
- Danh sách của Chống Lừa Đảo, tinnhiemmang.vn: đọc điều khoản trước khi dùng tự động; nếu không rõ, chỉ dẫn link cho người dùng tự tra.
