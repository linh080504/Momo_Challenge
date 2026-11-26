# apps/web — Trước Khi Chuyển (giao diện người dùng)

Next.js 16 (App Router, Cache Components) + Tailwind CSS 4. Chữ nhỏ nhất của toàn site là **18px**.

## Chạy local

```bash
cd apps/web
npm install
npm run dev          # http://localhost:3000
npm run lint && npx tsc --noEmit
npm run build        # kiểm tra bản production
```

API mặc định `http://localhost:8000`. Đổi bằng biến môi trường (xem `.env.example` ở gốc repo):

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Biến `NEXT_PUBLIC_*` được nhúng lúc build, nên đổi xong phải chạy lại `npm run dev` / `npm run build`.
BE phải cho phép origin `http://localhost:3000` trong `ALLOWED_ORIGINS` khi chạy local.

## Cấu trúc

| Đường dẫn | Việc |
|---|---|
| `components/Checker.tsx` | Điều phối 4 màn: nhập → đang kiểm tra → kết quả / lỗi |
| `components/InputPanel.tsx` | Ô dán chữ, khu thả ảnh (chọn/kéo thả/Ctrl+V), nút **Dùng mẫu**, nút **Kiểm tra** |
| `components/ProgressScreen.tsx` | Màn tiến trình 3 chặng |
| `components/ResultCard.tsx` | Thẻ kết quả, chỉ đọc JSON theo `analysis.schema.json` |
| `components/ErrorPanel.tsx` | Lỗi: luôn nhắc "đừng chuyển tiền khi chưa có kết quả" |
| `lib/api.ts` | Gọi `POST /v1/analyze` (JSON base64) |
| `lib/image.ts` | Nén ảnh ở trình duyệt: cạnh dài ≤ 1600px, JPEG, base64 thuần |
| `lib/types.ts` | Kiểu theo schema + `parseAnalysis` (sai hình dạng thì báo lỗi, không vẽ thẻ thiếu mảnh) |
| `lib/labels.ts` | Đổi tên enum sang tiếng Việt. Không tính hay sửa mức nguy cơ |
| `lib/samples.ts` | Tin nhắn mẫu cho **Dùng mẫu** |

## Quy tắc giao diện cần giữ

- **Dùng mẫu chỉ điền sẵn ĐẦU VÀO.** Kết quả vẫn do API phân tích thật. Không đặt kết quả dựng sẵn ở bất kỳ đâu
  (brief mục 4, "Won't": demo kịch bản cứng).
- **Không giả tiến trình.** Màn chờ chỉ đánh dấu "Xong / Đang làm / Chờ" khi máy chủ gửi sự kiện thật. Chưa có sự kiện
  thì hiện danh sách 3 việc kèm vòng chờ, không có bước nào được đánh dấu xong. Tuyệt đối không hiện kết luận rủi ro sơ bộ.
- **Lỗi không bao giờ trông như "an toàn".** Mọi lỗi hiện "Chưa kiểm tra được" và nhắc đừng chuyển tiền.
- Mức nguy cơ luôn có **màu + chữ + biểu tượng**. Mức "thấp" cố ý không dùng chữ "an toàn".
- Không dùng `text-sm` / `text-xs`. Không khóa zoom.
- Cache Components: không gọi `Date.now()` / `Math.random()` khi render; chỉ dùng trong effect / event handler.

## Tiến trình thật — ĐỀ XUẤT, chờ BE và PM

Hợp đồng `POST /v1/analyze` hiện chỉ trả **một JSON ở cuối**, nên chưa có sự kiện tiến trình. `lib/api.ts` đã sẵn sàng nhận
NDJSON nếu máy chủ hỗ trợ (client gửi `Accept: application/x-ndjson`; máy chủ không hỗ trợ thì cứ trả JSON như cũ):

```
{"done":"read"}                                         đã đọc xong ảnh / tin nhắn
{"done":"entities","entities":[{"type":"URL","display":"vcb-xacthuc.top"}]}   chỉ `display` đã che
{"done":"evidence"}                                     đã tra xong bằng chứng
{"result":{ ...đúng analysis.schema.json... }}          kết quả cuối
{"error":"..."}                                         lỗi giữa chừng
```

Sự kiện tiến trình **không được** mang mức nguy cơ. Đây là thay đổi hợp đồng nên phải ghi `docs/DECISIONS.md` trước khi BE làm.
