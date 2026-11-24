# Tham chiếu API bằng chứng

## Google Safe Browsing Lookup API v4

- Tài liệu: https://developers.google.com/safe-browsing/v4/lookup-api
- `POST https://safebrowsing.googleapis.com/v4/threatMatches:find?key=API_KEY`
- Body tối thiểu:

```json
{
  "client": {"clientId": "truoc-khi-chuyen", "clientVersion": "0.1"},
  "threatInfo": {
    "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
    "platformTypes": ["ANY_PLATFORM"],
    "threatEntryTypes": ["URL"],
    "threatEntries": [{"url": "http://example.com/"}]
  }
}
```

- Phản hồi rỗng `{}` = không có trong danh sách (KHÔNG có nghĩa là an toàn). Có `matches` = nguy hiểm.
- Lookup API gửi URL thô lên Google; nêu điều này trong chính sách quyền riêng tư.
- Kiểm tra điều khoản sử dụng (mục đích thương mại có thể cần Web Risk API).

## RDAP

- `GET https://rdap.org/domain/<domain>` → `events[]` có `eventAction: "registration"`.
- Tên miền `.vn` do VNNIC quản lý thường không trả RDAP; trả `null` và không trừ điểm.

## Danh sách trắng ban đầu

Xem `OFFICIAL` trong `scripts/domain_check.py`. Kiểm chứng từng tên miền bằng cách mở website chính thức trước khi đưa vào sản phẩm; chuyển sang bảng DB `official_domains` để chuyên viên vận hành sửa được.

## Bảng DB gợi ý (Postgres/Supabase)

```sql
create table entities (
  id uuid primary key default gen_random_uuid(),
  type text check (type in ('ACCOUNT','PHONE','URL','DOMAIN','EMAIL')),
  value_hash text not null,           -- sha256 của giá trị đã chuẩn hóa
  display text,                       -- 0123****89
  status text default 'reported' check (status in ('reported','approved','rejected')),
  report_count int default 0,
  campaign_id uuid,
  approved_by uuid, approved_at timestamptz,
  created_at timestamptz default now(),
  unique (type, value_hash)
);
```
