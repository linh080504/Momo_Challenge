# Nguồn dữ liệu eval — Trước Khi Chuyển

Cập nhật: 2026-11-26 (đợt 2) · Người giữ: eval-qa · Trạng thái: **32 mẫu chính + 1 mẫu pool**, chưa đạt mục tiêu 100 mẫu.
Bảng mục 1 dùng được cho mục "Tài nguyên có sẵn" của README.

## Vietnamese Quality-Assured SMS Scam Dataset

Tran Nguyen Thai Tuan, Le Hoang Khang, Nguyen Minh Tai, Nguyen Van Thang và Mai Hoang Dinh công bố bộ SMS tiếng Việt theo CC BY 4.0. Bản đang dùng được ghim tại `a90e2bd7e8df2376939658075ba8094dcee488ad`. Nguồn mô tả tin nhắn đã ẩn danh bằng các token chuẩn. Nhãn `0` là hợp lệ và nhãn `1` gộp spam với lừa đảo. Bộ này có dữ liệu văn bản và nhãn nhị phân. Việc đánh giá thủ đoạn hoặc vùng bằng chứng cần tập được gán nhãn riêng. [Bản phát hành có tệp CSV](https://huggingface.co/datasets/trannguyenthaituan/vietnamese_sms_dataset/tree/a90e2bd7e8df2376939658075ba8094dcee488ad) · [Mô tả và tác giả](https://github.com/trannguyenthaituan251209/vietnamese_sms_dataset)

Giữ ranh giới train/test của nguồn. Công cụ chuẩn hóa Unicode, chữ hoa thường và khoảng trắng để phát hiện trùng. Tập test loại các bản sao có mặt trong train, các bản trùng trong test và bản có nhãn xung đột. Sau rà có 2.061 mẫu train và 536 mẫu test, trong đó test có 424 hợp lệ và 112 spam/lừa đảo. Manifest ghi số mẫu đã loại, checksum nguồn và checksum đầu ra. CSV, JSONL và báo cáo chi tiết ở `eval/generated/vsms/`. [Cách tái lập](../eval/README.md#bộ-sms-tiếng-việt-vsms)

## Nguồn benchmark bổ sung cho FraudURL

PhiUSIIL Phishing URL (Website) của Arvind Prasad và Shalini Chandra, UCI, 2024, giấy phép CC BY 4.0. Dùng nhãn công bố để so sánh LightGBM và XGBoost. Bộ chuẩn bị đọc URL và nhãn offline, chuẩn hóa về hostname, lấy một mẫu trên mỗi tên miền đăng ký và khóa ba tập theo tên miền. Nhãn do nguồn công bố. Tập này đo khả năng phân biệt URL trong nguồn PhiUSIIL và được theo dõi riêng với mẫu Việt Nam của đội. [UCI PhiUSIIL](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset) · [Cách tái lập benchmark](../eval/README.md#benchmark-fraudurl-trên-tập-uci)

## 1. Nguồn đang dùng

| Nguồn | Loại | Điều kiện dùng | Mẫu trong `dataset.jsonl` | Mẫu trong `pool/` |
|---|---|---|---|---|
| [Tuổi Trẻ Online](https://tuoitre.vn) | Ảnh chụp tin nhắn/email/văn bản giả do nạn nhân, công an, EVN, bệnh viện, trường đại học cung cấp cho báo; trích dẫn nguyên văn trong ngoặc kép | Bản quyền thuộc báo và bên cung cấp ảnh. **Chưa kiểm tra điều khoản chi tiết**, không tìm thấy giấy phép mở. Chỉ dùng nội bộ để đánh giá, ghi nguồn và link bài; không phát hành lại ảnh ngoài repo | 13 (11 ảnh, 2 văn bản) | 0 |
| [Dân trí](https://dantri.com.vn) | Ảnh chụp SMS/Zalo do Cục CSGT, Công an Quảng Ninh, Công an Cần Thơ, người dân cung cấp | Như trên | 6 (6 ảnh) | 0 |
| [MoMo — An toàn bảo mật](https://www.momo.vn/an-toan-bao-mat) | (a) đồ họa minh họa MoMo tự dựng; (b) kịch bản 2 cuộc gọi tự động **chính thức** của MoMo, MoMo trích trong bài blog | Nội dung của MoMo, như trên | 3 (1 ảnh `official_mock`, 2 văn bản legit) | 0 |
| [Vietcombank — Nguyên tắc giao dịch an toàn](https://www.vietcombank.com.vn/vi-VN/KHCN/Danh-sach-nguyen-tac-GDAT) | Thông điệp tổng đài tự động giả danh ngân hàng, Vietcombank trích trong cảnh báo của chính mình | Nội dung của Vietcombank, như trên | 1 (1 văn bản scam) | 0 |
| [Vietnamese Spam SMS Filtering](https://github.com/pth1993/vie-spam-sms-filtering) — Pham & Le-Hong, [arXiv:1705.04003](https://arxiv.org/abs/1705.04003), 11/05/2017 | Tin SMS tiếng Việt có nhãn ham/spam | Repo **không có file LICENSE**; bài báo ghi "made available for research purpose". Chỉ dùng nghiên cứu/đánh giá, không dùng thương mại | 9 (5 ham + 4 quảng cáo bất động sản, đều legit) | 1 (`p005`, ambiguous) |
| **Tổng** | | | **32** (18 ảnh, 14 văn bản) | **1** |

**Giới hạn đã gặp của nguồn Pham & Le-Hong:** repo công khai chỉ có `src/data_sample` gồm **10 dòng** (5 spam, 5 ham), không phải bộ 6.599 tin trong bài báo. Bài báo chú thích "github.com/pth1993" nhưng tài khoản này không có repo nào khác về SMS (xem 30 repo ở trang đầu danh sách, và tìm GitHub `vietnamese sms spam user:pth1993` chỉ ra 1 kết quả là repo này). Cả 10 dòng đã dùng hết (9 vào tập chính, 1 ở pool). Quyết định PM 2026-11-26: không chờ tác giả.

## 2. Nguồn đã thử nhưng chưa có mẫu

| Nguồn | Kết quả |
|---|---|
| `eval/inbox/` (tin PM và người quen gửi, đã che) | **Không tồn tại** ở bất kỳ worktree nào (`momo`, `momo-data`, `momo-ai`, `momo-api`, `momo-web`) hay nhánh remote tại thời điểm 2026-11-26. Cần PM đặt file vào `eval/inbox/` (hoặc cho biết đường dẫn); chưa có mẫu nào từ nguồn này |
| khonggianmang.vn | Không truy cập được: `net::ERR_NAME_NOT_RESOLVED` (thử cả `www.`) |
| momo.vn → Thông báo (`/tin-tuc/thong-bao`) | Truy cập được, 9 bài. **Chỉ đọc danh sách (slug bài), chưa mở từng bài**; các slug đều là thông báo tính năng (Vietlott SMS, hạn mức thanh toán, liên kết ứng dụng, bảo hiểm an toàn chuyển tiền...), nên chưa có mẫu. Có thể còn tin mẫu trong nội dung bài |
| momo.vn → Blog An toàn bảo mật (`/an-toan-bao-mat/blog`) | Truy cập được, 9 bài; đã đọc 8 (chưa đọc bài ransomware). Dùng bài `028 7306 5555` và `028 8888 5555` cho 2 mẫu legit (l010, l011). Các bài còn lại ("MoMo có lừa đảo không?", đầu số 081, Túi Thần Tài, link bị lộ, `028 5555 5555`, `028 9999 5555`) chỉ mô tả hoặc trích đoạn rời có dấu "..." → bỏ. Mục "Tình huống Cảnh giác" chỉ có bài giới thiệu tính năng |
| Vietcombank | Mục "Nguyên tắc giao dịch an toàn" có 4 bài: 1 bài cho mẫu s021; bài điểm thưởng hết hạn (18/07/2025) chỉ nêu danh sách tên miền, không có nguyên văn tin; bài Run & Share chỉ mô tả; bài 22/05/2025 trùng nội dung bài 04/04/2025 |
| BIDV | Trang An toàn & Bảo mật chỉ có nguyên tắc bảo mật chung, không có tin mẫu |
| Techcombank, VietinBank | Các đường dẫn cảnh báo đoán thử trả 404; trang chủ không có liên kết cảnh báo hiển thị. **Chưa quét hết** (chưa dùng được công cụ tìm kiếm trong trang) |
| Công an tỉnh / Bộ Công an (`.gov.vn`, CAND) | Đã đọc: Công an Lai Châu 18/03/2023, báo Công an nhân dân 06/08/2023 "Bài 5", Báo Lào Cai 31/07/2026 (Công an xã Phúc Khánh). **Cả 3 bài chỉ mô tả**, không có tin nguyên văn → 0 mẫu. Riêng cảnh báo "con đang cấp cứu" của Bộ Công an có ảnh nguyên văn, lấy qua Tuổi Trẻ (s017) |
| VnExpress | Tìm kiếm trả 2 bài, cả hai chỉ mô tả (trạm BTS giả) → bỏ |
| Thanh Niên | Tìm kiếm không trả bài liên quan |
| Báo khác (VTV, Nhân Dân, Báo Lào Cai...) | Không thuộc danh sách PM cho phép, chỉ dùng để đối chiếu, không lấy mẫu |

## 3. Ảnh đã xem và loại (để không xét lại)

| Nguồn | Lý do loại |
|---|---|
| Tuổi Trẻ 22/08/2026 (infographic Công an Quảng Ninh) | Đồ họa có sẵn lời khuyên ("CẢNH BÁO...") nên lộ đáp án; cùng kịch bản với s003, s013 |
| Tuổi Trẻ 28/11/2025 (người cầm điện thoại), 14/11/2026 và 15/11/2026 (Zalo minh họa) | Ảnh minh họa: không có chữ đọc được, hoặc chữ bị làm mờ |
| Tuổi Trẻ 16/11/2026 (Zalo mượn 30 triệu) | Cùng tin nhắn và cùng sự kiện với s012 (ảnh khác) → khử trùng |
| Tuổi Trẻ 25/12/2025 (ghép 6 ảnh "người đẹp" dụ qua Campuchia) | Ảnh chụp mờ, chữ không đọc được; kịch bản G3.4 nên đáng lấy nếu tìm được bản rõ |
| Tuổi Trẻ 20/05/2026 (thẻ nhân viên trường, chứng từ chi giả của bệnh viện) | Không phải tin nhắn; là kiểu mạo danh bệnh viện/trường để lừa **nhà cung cấp** đặt cọc, nằm ngoài G1.7 hiện tại |
| Tuổi Trẻ 29/06/2026 (trang TikTok giả "Hỏi đáp tuyển sinh") | Không có tin lừa đảo, chỉ là trang mạo danh |
| Tuổi Trẻ 31/07/2025 (ảnh ghép voucher, SMS mời nhận thưởng) | SMS bị cắt dở, ảnh có tên, SĐT, địa chỉ, chữ ký viết tay; che hết sẽ mất ý nghĩa |
| Tuổi Trẻ 24/07/2025 (infographic TTXVN VNeID giả), 19/10/2026 (infographic thẻ BHXH điện tử) | Infographic, không có tin nhắn nguyên văn |
| Dân trí 22/10/2026 (thiệp cưới), 11/10/2026 (infographic Công an Hưng Yên về BHXH) | Infographic, không có tin nhắn nguyên văn |
| Dân trí 27/10/2026 (trang EVN giả cạnh trang thật) | Ảnh so sánh 2 trang, có nhãn "FAKE"; chưa dùng |
| Dân trí 25/08/2026 (SMS phạt nguội, 3 ảnh) | Mới xem 1 ảnh: điện thoại chế độ tối cầm trên tay, chữ nhỏ khó đọc; **2 ảnh còn lại chưa xem**. Cùng kịch bản G1.2 với s004, s005, s010 (đã có ba mẫu G1.2) nên chưa ưu tiên |
| Dân trí 23/11/2026 (tin nhắn "anh yêu" sau khi bị phát hiện) | Không xác định được bong bóng nào là của kẻ lừa đảo; ảnh cắt cận, chưa đủ ngữ cảnh |
| MoMo bản tin số 1: ảnh fanpage "Nemo House" và ảnh shipper + QR | Ảnh câu đố, nhãn chỉ có trong ảnh giải đáp, bản thân ảnh không phải tin lừa đảo rõ ràng → ambiguous |

## 4. Quy ước đã áp dụng

**Chọn mẫu.** Chỉ lấy khi bài có tin nhắn/ảnh nguyên văn (ngoặc kép dài hoặc ảnh đọc được). Bài chỉ mô tả thì bỏ. Mỗi mẫu có `source_url` và `source_date` (ngày đăng bài; riêng bộ Pham & Le-Hong là ngày đưa lên arXiv; riêng MoMo bản tin số 1 là ngày hiển thị trên trang; riêng MoMo blog là `datePublished` trong JSON-LD của trang). `synthetic` luôn là `false`. Khử trùng lặp: cùng một tin chỉ giữ một bản (trích dẫn báo trùng với ảnh thì giữ ảnh; hai cảnh báo của cùng ngân hàng trùng nội dung thì giữ bản đăng sớm hơn). Cùng kịch bản nhưng khác thương hiệu/tên miền (s003 VIB, s013 BIDV) giữ cả hai và ghi chú.

**Trường thêm so với `dataset-guide.md`** (PM đã biết từ báo cáo đợt 1; chờ PM ghi `docs/DECISIONS.md` vì thuộc `docs/**`):
- `source_url`, `source_date`: theo yêu cầu.
- `scenario_id`: mã kịch bản con theo `taxonomy.md`.
- `provenance`: `screenshot` (ảnh chụp màn hình thật) · `photo` (chụp màn hình điện thoại bằng máy ảnh) · `official_mock` (đồ họa do cơ quan/ngân hàng/ví dựng lại, **không phải tin của nạn nhân**; không tính vào chỉ tiêu ảnh thật) · `quote` (trích nguyên văn trong bài) · `dataset` (bộ nghiên cứu). Giá trị `illustration` của đợt 1 đã đổi thành `official_mock` (quyết định PM 2026-11-26).
- `notes`: ghi chú về cách xử lý (che gì, ghép trích dẫn thế nào, chỗ nghi nhãn).
- Tag `annotated`: ảnh gốc đã có dấu X đỏ, dấu "GIẢ MẠO" hoặc chú thích do nguồn thêm. Quyết định PM: giữ tag, **báo recall riêng**, đợt sau ưu tiên ảnh không chú thích. Hiện 7 ảnh annotated / 11 ảnh không chú thích (không tính `official_mock`: 10).
- Tag `stitched`: văn bản do ghép nhiều trích dẫn rời trong cùng bài (hiện: s016).

**Nhãn.** `group` theo `taxonomy.md`. Nghi ngờ nhãn → tag `ambiguous` và đưa vào `eval/pool/`, không đưa vào tập chấm điểm chính (theo `dataset-guide.md`). Quy ước PM: tin thường → legit; tin quảng cáo → legit + `hard_negative`. Quyết định PM 2026-11-26: 4 tin quảng cáo bất động sản của bộ Pham & Le-Hong (l006–l009) vào tập chính; tin quảng cáo trúng thưởng "từ MobiFone" (`p005`) giữ `ambiguous` ở pool vì giống kịch bản G4.4.

**Mẫu nên được người gán thứ hai xem kỹ** (nhãn dựa vào bài báo, nội dung mẫu tự nó không đủ để nhận ra):
- s019 (Zalo đặt phòng, bên bán): ảnh không có dấu hiệu lừa đảo, nhãn scam dựa vào bài.
- s021 (cuộc gọi tự động chào mở thẻ tín dụng): giống hệt cuộc gọi chào bán thật của ngân hàng.
- s017 (SMS "bé bị té, cần phẫu thuật gấp"): ảnh do Bộ Công an công bố, bài không nói rõ là tin nhắn thật hay dựng lại.
- Mã kịch bản chưa chắc: s001 (G5.1 hay G1.3), s009 (G4.4 hay G5.2), s021 (G1.5 hay G5.4), s019 (G4.2 hay G4.1).

**Ẩn danh.**
- Văn bản: `eval/tools/anonymize.py` chạy `pii_mask.py` rồi thay bằng giá trị giả nhất quán trong toàn tập (SĐT `0900xxxxxx`, tài khoản `9999…`, email cá nhân `@example.com`). Bảng ánh xạ thật→giả nằm **ngoài repo**. Tên miền và link giữ nguyên. Build **dừng** nếu giá trị thật còn sót trong đầu ra (đã chặn một lần ở đợt 2, xem dưới).
- Ảnh: `eval/tools/redact_image.py` tô ô đen đặc (không làm mờ) lên tên, ảnh đại diện, SĐT, số tài khoản, mã QR chứa số tài khoản, tên người ký trên văn bản giả; lưu lại từ điểm ảnh nên mất EXIF. Có ảnh cắt bớt (s003, s009) để bỏ tay, tóc, khung câu hỏi. Ảnh gốc để ngoài repo; muốn dựng lại phải tải lại từ `source_url`. Mỗi ảnh đã được xem lại bằng mắt sau khi che.
- Ngoại lệ có chủ ý: (1) mã OTP trong SMS giả EVN (s001) giữ nguyên vì là mã do kẻ lừa đảo gửi và vẫn hiện trong ảnh. (2) **Email vai trò của tổ chức** (`info@`, `hanhchinh@`... trong s020: `info@hcmus.edu.vn`, `info@uef.edu.vn`, `info@uif.edu.vn`, `hanhchinh@hcmussh.edu.vn`) giữ nguyên vì là bằng chứng lừa đảo (tên miền nhái trường) và không gắn với cá nhân; validator chỉ chấp nhận đúng danh sách vai trò cố định (`ROLE_MAILBOXES`), email khác phải là `@example.com`. (3) Một số nguồn đã làm mờ/che sẵn (biển số, tên thí sinh); đã che đen thêm ở chỗ còn đọc được.
- Giới hạn: tên người và địa chỉ trong **văn bản** không có công cụ tự động; đã kiểm tay từng mẫu (không còn tên người thật; "Châu" trong l002 là tên riêng một chữ trong bộ dữ liệu nghiên cứu). Phần chép lại nội dung ảnh (`transcript`) do eval-qa tự đọc, chưa có người thứ hai đối chiếu.

**Sự cố ghi nhận (đợt 2).** Khi giữ nguyên email vai trò, bảng ánh xạ cũ vẫn chứa 4 email đã bị đổi ở lần dựng trước, nên bước kiểm tra rò rỉ báo "4 giá trị thật còn trong đầu ra" và dừng dựng, giữ nguyên `dataset.jsonl` cũ. Đã xoá mục email cũ khỏi bảng ánh xạ và dựng lại; không có giá trị thật nào vào repo.

## 5. Nhãn thứ hai (blind20)

`eval/blind20.csv`: 20 mẫu đầu theo **thứ tự thu thập** (s001–s016, l001–l004), xáo thứ tự bằng seed cố định, **không kèm nhãn**. Chỉ có `blind_id` (b01–b20), kênh, văn bản, đường dẫn ảnh. Ảnh đã chép sang `eval/blind20/bNN.png` (tên trung tính) vì tên `sNNN`/`lNNN` lộ nhãn; không có `transcript`, tag, nguồn. Bảng đối chiếu `eval/blind20.key.csv` chỉ có `blind_id → id`, nhưng chữ đầu của `id` (`s`/`l`) cho biết nhãn: **người gán không mở file này trước khi điền xong**.

Cột người gán điền: `label (scam|legit)`, `group`, `scenario_id`, `chac_chan (y|n)`, `ghi_chu`. Điền xong chạy:

```bash
python3 eval/tools/compare_blind20.py          # đồng thuận nhãn, kappa, danh sách mẫu lệch
```

Lưu ý: tỷ lệ scam/legit của 20 mẫu này không cân bằng (do thứ tự thu thập; số cụ thể xem ở `eval/blind20.key.csv` **sau khi gán xong**), và 6 ảnh có dấu X/"GIẢ MẠO" nên tự lộ đáp án; kết quả đồng thuận vì thế có thể cao hơn thực tế. Mẫu lệch → ghi `docs/DECISIONS.md` và hỏi PM, **không sửa nhãn** (quy tắc eval-qa). Xong việc có thể xoá `eval/blind20/` để repo nhẹ.

## 6. Kiểm tra và công cụ

```bash
python3 eval/tools/validate_dataset.py eval/dataset.jsonl --min-total 100 --min-images 20 --min-g17 2 --min-per-group 10 --max-source dataset-pham-lehong=25
python3 eval/tools/validate_dataset.py eval/pool/pham-lehong-ads.jsonl --pool
python3 eval/tools/recall_by_tag.py eval/reports/<stamp>-<tag>.json --data eval/dataset.jsonl   # recall riêng ảnh annotated / không chú thích / official_mock / từng provenance / từng scenario
python3 eval/tools/compare_blind20.py
```

`validate_dataset.py` kiểm tra: đủ trường và đúng kiểu, `id` không trùng, file ảnh tồn tại và là PNG/JPEG thật ≤ 5 MB, mẫu ảnh có `text` rỗng và `transcript`, `synthetic=false`, `source_url` và `source_date` hợp lệ, không trùng văn bản/ảnh, không còn SĐT/STK/email cá nhân thật (chạy `pii_mask` lên `text` và `transcript`), không có `ambiguous` trong tập chính. `--min-images` chỉ đếm ảnh **không phải** `official_mock`.

## 7. Hiện trạng so với mục tiêu (2026-11-26, sau đợt 2)

| Hạng mục | Hiện có | Mục tiêu | Thiếu |
|---|---|---|---|
| Tổng mẫu chính | 32 | 100 | 68 |
| Ảnh thật (không `official_mock`) | 17 | 20 | 3 |
| G1.7 (mẫu thật) | 4 (s002, s007, s016, s017) | 2 | đã đạt; mới có 1 mẫu "báo cấp cứu" (s017), 3 mẫu còn lại là "đóng học phí" |
| Scam G1 / G2 / G3 / G4 / G5 | 12 / 4 / 1 / 3 / 1 | ≥ 10 mỗi nhóm | G2: 6 · G3: 9 · G4: 7 · G5: 9 |
| legit / hard_negative | 11 / 8 | 20 / 15 | 9 / 7 |
| injection | 0 | 5 | 5 (nguồn thật khó có; xem đề xuất ở báo cáo) |
