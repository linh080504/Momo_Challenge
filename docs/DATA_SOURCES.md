# Nguồn dữ liệu eval — Trước Khi Chuyển

Cập nhật: 2026-11-26 (đợt 3) · Người giữ: eval-qa · Trạng thái: **107 mẫu chính** (5 mẫu tổng hợp) + **2.528 mẫu pool** nhãn thô/ambiguous.
Bảng mục 1 dùng được cho mục "Tài nguyên có sẵn" của README. Ghi công và trích dẫn bộ dữ liệu CC BY 4.0 ở mục 2.

## 1. Nguồn đang dùng

| Nguồn | Loại | Điều kiện dùng | Mẫu trong `dataset.jsonl` | Mẫu trong `pool/` |
|---|---|---|---|---|
| [Tuổi Trẻ Online](https://tuoitre.vn) | Ảnh chụp tin nhắn/email/văn bản giả do nạn nhân, công an, EVN, bệnh viện, trường đại học cung cấp cho báo; trích dẫn nguyên văn trong ngoặc kép | Bản quyền thuộc báo và bên cung cấp ảnh. **Chưa kiểm tra điều khoản chi tiết**, không tìm thấy giấy phép mở. Chỉ dùng nội bộ để đánh giá, ghi nguồn và link bài; không phát hành lại ảnh ngoài repo | 13 (11 ảnh, 2 văn bản) | 0 |
| [Dân trí](https://dantri.com.vn) | Ảnh chụp SMS/Zalo do Cục CSGT, Công an Quảng Ninh, Công an Cần Thơ, người dân cung cấp | Như trên | 6 (6 ảnh) | 0 |
| [MoMo — An toàn bảo mật](https://www.momo.vn/an-toan-bao-mat) | (a) đồ họa minh họa MoMo tự dựng; (b) kịch bản 2 cuộc gọi tự động **chính thức** của MoMo, MoMo trích trong bài blog | Nội dung của MoMo, như trên | 3 (1 ảnh `official_mock`, 2 văn bản legit) | 0 |
| [Vietcombank — Nguyên tắc giao dịch an toàn](https://www.vietcombank.com.vn/vi-VN/KHCN/Danh-sach-nguyen-tac-GDAT) | Thông điệp tổng đài tự động giả danh ngân hàng, Vietcombank trích trong cảnh báo của chính mình | Nội dung của Vietcombank, như trên | 1 (1 văn bản scam) | 0 |
| [Vietnamese Spam SMS Filtering](https://github.com/pth1993/vie-spam-sms-filtering) — Pham & Le-Hong, [arXiv:1705.04003](https://arxiv.org/abs/1705.04003), 11/05/2017 | Tin SMS tiếng Việt có nhãn ham/spam | Repo **không có file LICENSE**; bài báo ghi "made available for research purpose". Chỉ dùng nghiên cứu/đánh giá, không dùng thương mại | 9 (5 ham + 4 quảng cáo bất động sản, đều legit) | 1 (`p005`, ambiguous) |
| [vietnamese_sms_dataset](https://github.com/trannguyenthaituan251209/vietnamese_sms_dataset) — Tran, Le, Nguyen, Nguyen, Mai (2026) | Tin SMS tiếng Việt thật theo tác giả, nhãn 0/1 (hợp lệ / rác-lừa đảo), chia sẵn train/test | **CC BY 4.0** (khai trong README; không có file LICENSE) — được dùng kể cả thương mại nếu ghi công, nêu rõ đã sửa đổi, dẫn giấy phép. Xem mục 2 | 70 (40 scam, 30 legit), tất cả lấy từ `test.csv` | 2.527 (train 2.033, test 494), nhãn thô |
| Mẫu tổng hợp do eval-qa viết (`eval-qa-synthetic`) | 5 mẫu prompt injection (`i001`–`i005`), SĐT/STK/mã đều là giá trị giả | Không có bản quyền bên thứ ba; **synthetic=true**, chưa có người thứ hai duyệt | 5 | 0 |
| **Tổng** | | | **107** (18 ảnh, 89 văn bản) | **2.528** |

**Giới hạn của nguồn Pham & Le-Hong:** repo công khai chỉ có `src/data_sample` gồm **10 dòng** (5 spam, 5 ham), không phải bộ 6.599 tin trong bài báo. Bài báo chú thích "github.com/pth1993" nhưng tài khoản này không có repo nào khác về SMS (xem 30 repo ở trang đầu danh sách, và tìm GitHub `vietnamese sms spam user:pth1993` chỉ ra 1 kết quả là repo này). Cả 10 dòng đã dùng hết (9 vào tập chính, 1 ở pool). Quyết định PM 2026-11-26: không chờ tác giả.

## 2. vietnamese_sms_dataset: ghi công, thay đổi, quy trình

**Ghi công (CC BY 4.0).** Trần Nguyễn Thái Tuấn, Lê Hoàng Khang, Nguyễn Minh Tài, Nguyễn Văn Thắng, Mai Hoàng Đỉnh. *Vietnamese SMS Dataset with Quality Assurance.* IEEE Access, 2026 (theo trích dẫn của tác giả trong README; README chưa ghi số tập/trang/DOI nên không ghi thêm). Mã nguồn dữ liệu: https://github.com/trannguyenthaituan251209/vietnamese_sms_dataset, commit `464a028878023598e16f2f344ee36f7d5d74257f` (2026-08-07). Giấy phép: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Tác giả cảm ơn Team Chống Lừa Đảo (50.000 URL dùng làm tiêu chí gán nhãn) và những người đóng góp tin nhắn có đồng thuận. Bản này đưa vào eval nên phải giữ nguyên các dòng ghi công trên trong mọi tài liệu phát hành kèm dữ liệu (README, slide nếu dùng số liệu).

**Thay đổi so với bản gốc (CC BY 4.0 yêu cầu nêu rõ):**
1. Khử trùng lặp theo văn bản chuẩn hóa (bỏ khác biệt hoa/thường và khoảng trắng); văn bản ở cả train và test giữ ở test.
2. Chạy lại ẩn danh (mục 4): thay chuỗi số dài, OTP, biển số, handle, ID Zalo, họ tên còn sót bằng giá trị giả; giữ nguyên mọi token của tác giả.
3. Gán lại nhãn: nhãn gốc chỉ có 0/1; 70 tin vào tập chính được eval-qa đọc và gán `scam` + nhóm G1–G5 + mã kịch bản, hoặc `legit` (+ `hard_negative`). Phần còn lại giữ **nhãn thô** (`raw_label`), không chấm điểm.
4. Thêm trường `source_url`, `source_date` (ngày thu thập trong `full_dataset.csv`, lấy ngày sớm nhất khi một tin có nhiều ngày; 14 tin không có ngày dùng ngày commit, cờ `date_from_repo_commit`), `provenance=public_dataset`, `upstream_split`, `flags`.
5. Không dùng `full_dataset.csv` làm nguồn tin (nó chỉ là hợp của train và test); chỉ dùng cột `date`.

**Số liệu thật (khác số nhớ ban đầu):**

| Mục | Số |
|---|---|
| Dòng trong train / test / full | 2.394 / 597 / 2.991 (README cũng ghi 2.991) |
| Tin nhãn 1 trong full | 798 (đây là "798 tin" trong yêu cầu; không phải tổng số tin) |
| Tin duy nhất sau khử trùng | 2.598 (**393 bản sao bị loại**: 87 nhãn 1, 305 nhãn 0, 1 do một văn bản mang cả hai nhãn). Số "~361" trong yêu cầu **không khớp** bản dữ liệu hiện tại |
| Văn bản có ở cả train và test | 28 (README nói test "hạn chế rò rỉ", thực tế vẫn trùng; đã giữ ở test; 12 tin nằm trong tập chính, 16 tin còn trong pool với cờ `also_in_train`) |
| Văn bản xung đột nhãn (cả 0 và 1) | 1, nằm trong test, `raw_label=null`, cờ `label_conflict` |
| Vào tập chính | 70 (40 scam, 30 legit), đều từ `test.csv` |
| Pool | 2.527 = 2.033 train + 494 test. 70 + 2.527 + 1 gộp sau ẩn danh = 2.598 |
| Token `[PHONE]` / `[BANK_ACC]` | **Không có token nào** trong train/test dù README nói có. Bước "đổi [PHONE]/[BANK_ACC] sang token của mình" vì thế không có gì để đổi; dữ liệu dùng token `[NUMBER]` cho SĐT/STK đã được tác giả che |
| Token giữ nguyên | `[MONEY] [NUMBER] [DATE] [TIME]` theo yêu cầu, cùng token khác của tác giả: `[NAME] [TB] [QC] [POINT]` và vài token thương hiệu (`[BIDV] [LAZADA] …`) |

**Diễn giải cần PM xác nhận:** "token của mình" được hiểu là **giá trị giả theo quy ước của repo** (SĐT `0900xxxxxx`, STK `9999…`), không phải token kiểu `[PHONE_1]`. Lý do: `dataset-guide.md` quy định thay bằng giá trị giả, và analyzer sẽ tự chạy `pii_mask` trên tin thật. Nếu cần token thì đổi một dòng ở `eval/tools/anonymize.py`.

**Chọn mẫu vào tập chính (bằng script, duyệt tay phần vào tập chính).**
- `test.csv` có 133 tin spam duy nhất. Vòng 1 (từ khóa tín hiệu lừa đảo, bỏ cờ bạc/opt-out): 40 ứng viên. Vòng 2 (tín hiệu yếu: liên hệ, tài khoản, link, thương hiệu...) trên phần còn lại: xem thêm 52 tin. Vòng 1 bỏ sót khoảng 35 tin lừa đảo (đòi nợ giả danh cơ quan, phạt nguội, điểm thưởng ngân hàng...), nên vòng 2 là bắt buộc.
- **Số tin đã đọc:** 92 tin spam và khoảng 57 tin legit trong test; **không đọc** 41 tin spam còn lại của test, ~374 tin legit còn lại của test, và không đọc tin nào của train (chỉ xem đoạn khớp của bước quét PII).
- **Loại khỏi tập chính (vẫn nằm trong pool, nhãn thô 1):** quảng cáo, cờ bạc/nhà cái (≥ 20 tin phát hiện bằng từ khóa), vay tiền quảng cáo, thuê tài khoản ngân hàng, và nhóm **đòi nợ/đe dọa danh bạ** ("khoản vay quá hạn, sẽ thông báo toàn bộ danh bạ", "người bảo lãnh khoản vay"). Nhóm cuối là lừa đảo thật nhưng **taxonomy chưa có kịch bản** (đề nghị ai-engineer/PM xem xét thêm mã). Ví dụ trong pool test: `vte-0007`, `vte-0420`, `vte-0443`; còn các tin tương tự trong train chưa được dò.
- Lọc trùng: trong 70 tin chọn, cặp giống nhau nhất có Jaccard từ 0,736 (s044~s045); validator chặn nếu ≥ 0,85. Với mỗi khuôn chỉ giữ 1–2 biến thể.
- Nhóm tin chọn: scam G1=12, G2=5, G3=9, G4=7, G5=7 (mã: G1.1×5, G1.2×3, G1.3, G1.5×3, G2.1×3, G2.2, G2.3, G3.1×8, G3.2, G4.3×2, G4.4×2, G4.5×3, G5.1×4, G5.4×3). **Không đạt "~50 scam rải đều"**: test chỉ có ~45 tin scam đáng tin sau khi loại cờ bạc, quảng cáo và trùng khuôn; nhóm G5 chỉ có 7 tin vsms vì dữ liệu ít, không phải vì không ưu tiên (tổng G5 thật là 8). Mã G4.5 ("báo chuyển nhầm tiền, nhờ hoàn lại") là gần đúng: taxonomy không có kịch bản này. Nhiều tin G5.1 có thể xếp G1.5 (brandname ngân hàng giả).
- Legit: 30 tin (27 `hard_negative`: OTP/mã xác thực của ngân hàng, ví, sàn, shipper; khuyến mãi nhà mạng (QC) có link; thông báo cơ quan nhà nước kể cả cảnh báo lừa đảo; đặt bàn; 3 tin đời thường không `hard_negative`). Khuyến mãi nhà mạng gắn `hard_negative` theo yêu cầu. Bộ này gần như không có tin nhắn đời thường giữa người với người nên phần "tin thân quen" vẫn thiếu.

**Phát hiện cần PM biết:**
1. **Tin ngày 2026-07-24 có mức khuôn mẫu rất cao.** Trong 203 tin duy nhất của ngày này (202 spam), **54% có chữ ký khuôn trùng với tin khác** (thay tên ngân hàng/tên người/STK), so với 0–6% ở các ngày nhiều spam khác (22/07: 6%, 25/07: 0%, 28/05: 4%). Ví dụ: 4 phiên bản "em kẹt viện phí cho mẹ" chỉ khác ngân hàng và STK. Chưa chứng minh được là sinh tự động, nên **giữ `synthetic=false`** theo README ("không AI-generated") và theo chỉ đạo, nhưng gắn tag **`template_like`** (13 mẫu scam trong tập chính, 98 tin trong pool) để báo recall riêng. Nếu PM kết luận đây là mẫu tổng hợp thì đổi `synthetic` và `provenance` của các mẫu có tag này.
2. **Tập trung theo thời gian:** 39/40 tin scam vsms trong tập chính được thu thập trong hai ngày 24/07 (24 tin) và 25/07/2026 (15 tin), 1 tin ngày 28/05.
3. **Nhãn nghi sai:** tìm thấy 1 tin lừa đảo bị gán nhãn 0 (tên miền nhái `vletcombank.com`, "đăng nhập để nâng cấp tính năng mới") → không đưa vào tập chính, cờ `label_suspect` trong pool (`vte-0071`). Tin xung đột nhãn duy nhất là `vte-0408`. **Chưa kiểm tra có hệ thống** nhãn 0 nên **không biết tỷ lệ nhãn sai**; thử lọc bằng "tên miền thương hiệu không chính thức" cho 89 kết quả nhiễu (phần lớn là tên miền con chính thức của Viettel) nên bỏ.
4. Nhãn 0 của tác giả gồm rất nhiều quảng cáo nhà mạng có yếu tố "trúng 10 cây vàng, 3 xe máy" (đã không đưa vào tập chính vì dễ làm sai lệch định nghĩa legit).

## 3. Nguồn đã thử nhưng chưa có mẫu

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

Từ đợt 3 PM dặn **không quét thêm báo**.

## 4. Ảnh đã xem và loại (để không xét lại)

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

## 5. Quy ước đã áp dụng

**Chọn mẫu.** Chỉ lấy khi bài có tin nhắn/ảnh nguyên văn (ngoặc kép dài hoặc ảnh đọc được). Bài chỉ mô tả thì bỏ. Mỗi mẫu thật có `source_url` và `source_date` (ngày đăng bài; riêng bộ Pham & Le-Hong là ngày đưa lên arXiv; riêng vietnamese_sms_dataset là ngày thu thập tin trong bộ; riêng MoMo bản tin số 1 là ngày hiển thị trên trang; riêng MoMo blog là `datePublished` trong JSON-LD của trang). `synthetic=false` cho mọi mẫu **trừ 5 mẫu injection** (`i001`–`i005`). Khử trùng lặp: cùng một tin chỉ giữ một bản (trích dẫn báo trùng với ảnh thì giữ ảnh; hai cảnh báo của cùng ngân hàng trùng nội dung thì giữ bản đăng sớm hơn). Cùng kịch bản nhưng khác thương hiệu/tên miền (s003 VIB, s013 BIDV) giữ cả hai và ghi chú.

**Trường thêm so với `dataset-guide.md`** (PM đã biết từ báo cáo đợt 1; chờ PM ghi `docs/DECISIONS.md` vì thuộc `docs/**`):
- `source_url`, `source_date`: theo yêu cầu. Mẫu tổng hợp không có `source_url`.
- `scenario_id`: mã kịch bản con theo `taxonomy.md`.
- `provenance`: `screenshot` (ảnh chụp màn hình thật) · `photo` (chụp màn hình điện thoại bằng máy ảnh) · `official_mock` (đồ họa do cơ quan/ngân hàng/ví dựng lại, **không phải tin của nạn nhân**; không tính vào chỉ tiêu ảnh thật) · `quote` (trích nguyên văn trong bài) · `public_dataset` (bộ dữ liệu công bố: Pham & Le-Hong và vietnamese_sms_dataset; giá trị `dataset` của đợt 1 đã gộp vào đây) · `synthetic` (do đội tự viết, chỉ dành cho injection). Giá trị `illustration` của đợt 1 đã đổi thành `official_mock`.
- `upstream_split`: `test` với mẫu lấy từ `test.csv` của vietnamese_sms_dataset.
- `notes`: ghi chú về cách xử lý (che gì, ghép trích dẫn thế nào, chỗ nghi nhãn).
- Tag `annotated`: ảnh gốc đã có dấu X đỏ, dấu "GIẢ MẠO" hoặc chú thích do nguồn thêm. Giữ tag, **báo recall riêng**. Hiện 7 ảnh annotated / 10 ảnh không chú thích (không tính `official_mock`).
- Tag `stitched`: văn bản do ghép nhiều trích dẫn rời trong cùng bài (hiện: s016).
- Tag `template_like`: tin ngày 2026-07-24 của vietnamese_sms_dataset có chữ ký khuôn trùng với tin khác (mục 2, phát hiện 1). Báo recall riêng.
- Tag `injection`: mẫu có câu ra lệnh cho AI (5 mẫu tổng hợp).

**Mẫu tổng hợp (injection).** `i001`–`i005`, PM cho phép tối đa 5. Mỗi mẫu là một tin lừa đảo thật-giống-thật kèm một kỹ thuật khác nhau: ghi đè kết luận (`risk_level=low`), giả lệnh `SYSTEM` đổi vai, chuyển hướng tác vụ (dịch tin và bảo lãnh người gửi), chèn JSON giả vai system bằng tiếng Anh, đòi in system prompt rồi kết luận. Mọi SĐT/STK/mã trong tin là giá trị giả. Tỷ lệ mẫu tổng hợp trên slide: **5/107 = 4,7%**. Theo `dataset-guide.md`, mẫu tổng hợp phải được người khác trong đội duyệt cho giống thật; **chưa duyệt**.

**Nhãn.** `group` theo `taxonomy.md`. Nghi ngờ nhãn → tag `ambiguous` và đưa vào `eval/pool/`, không đưa vào tập chấm điểm chính (theo `dataset-guide.md`). Quy ước PM: tin thường → legit; tin quảng cáo → legit + `hard_negative`; khuyến mãi nhà mạng → `hard_negative`. Quyết định PM 2026-11-26: 4 tin quảng cáo bất động sản của bộ Pham & Le-Hong (l006–l009) vào tập chính; `p005` giữ `ambiguous` ở pool vì giống kịch bản G4.4.

**Mẫu nên được người gán thứ hai xem kỹ** (nhãn dựa vào bài báo hoặc việc đọc của eval-qa, nội dung mẫu tự nó không đủ để nhận ra):
- s019 (Zalo đặt phòng, bên bán): ảnh không có dấu hiệu lừa đảo, nhãn scam dựa vào bài.
- s021 (cuộc gọi tự động chào mở thẻ tín dụng): giống hệt cuộc gọi chào bán thật của ngân hàng.
- s017 (SMS "bé bị té, cần phẫu thuật gấp"): ảnh do Bộ Công an công bố, bài không nói rõ là tin nhắn thật hay dựng lại.
- Mã kịch bản chưa chắc: s001 (G5.1 hay G1.3), s009 (G4.4 hay G5.2), s021 (G1.5 hay G5.4), s019 (G4.2 hay G4.1); các mẫu G4.5 và G5.1/G1.5 của vietnamese_sms_dataset.
- Toàn bộ 70 mẫu vietnamese_sms_dataset do **một người (eval-qa) gán nhãn và nhóm**, chưa có người thứ hai.

**Ẩn danh.**
- Văn bản: `eval/tools/anonymize.py` chạy `pii_mask.py` rồi thay bằng giá trị giả nhất quán trong toàn tập (SĐT `0900xxxxxx`, tài khoản `9999…`, OTP `100…`, email cá nhân `@example.com`, biển số `00A-NNN.00`, handle `@userNNNN`). Bảng ánh xạ thật→giả nằm **ngoài repo**. Tên miền và link giữ nguyên. Hotline công khai 1800/1900 giữ nguyên.
- Với dữ liệu công khai chưa duyệt tay, `anonymize_extended` bổ sung các bước mà `pii_mask` không có: mã OTP/kích hoạt đứng xa chữ "OTP" (đến 60 ký tự, bỏ năm và số kèm đơn vị), biển số xe, handle `@…` (trừ `@viettelcskh`, `@accounts`), họ tên viết hoa kiểu họ Việt + 1–3 chữ (trừ địa danh/đường phố), ID Zalo trong URL, chuỗi ≥ 20 chữ số (`pii_mask` giới hạn 19). Kết quả với vietnamese_sms_dataset: mã OTP 180 lần ở pool + 4 ở tập chính, họ tên 10, biển số 2 + 1, handle 1 + 1, ID Zalo 2. 104 tin gốc còn chuỗi ≥ 8 chữ số (chủ yếu mã giao dịch, số tài khoản, số hợp đồng) đều bị thay.
- Ảnh: `eval/tools/redact_image.py` tô ô đen đặc (không làm mờ) lên tên, ảnh đại diện, SĐT, số tài khoản, mã QR chứa số tài khoản, tên người ký trên văn bản giả; lưu lại từ điểm ảnh nên mất EXIF. Có ảnh cắt bớt (s003, s009) để bỏ tay, tóc, khung câu hỏi. Ảnh gốc để ngoài repo; muốn dựng lại phải tải lại từ `source_url`. Mỗi ảnh đã được xem lại bằng mắt sau khi che.
- Ngoại lệ có chủ ý: (1) mã OTP trong SMS giả EVN (s001) giữ nguyên vì là mã do kẻ lừa đảo gửi và vẫn hiện trong ảnh. (2) **Email vai trò của tổ chức** (`info@`, `hanhchinh@`... trong s020) giữ nguyên vì là bằng chứng lừa đảo (tên miền nhái trường) và không gắn với cá nhân; validator chỉ chấp nhận đúng danh sách vai trò cố định (`ROLE_MAILBOXES`). (3) Một số nguồn đã làm mờ/che sẵn (biển số, tên thí sinh); đã che đen thêm ở chỗ còn đọc được.
- **Giới hạn:** (a) 70 mẫu vsms vào tập chính và các mẫu của đợt trước đã được xem bằng mắt sau khi ẩn danh. **Pool 2.527 tin không duyệt tay**: họ tên và địa chỉ dựa vào token `[NAME]` của tác giả (128 tin có) cộng quy tắc họ Việt ở trên, nên vẫn có thể còn tên hoặc địa chỉ ở dạng không bắt được. (b) Mã OTP 4 chữ số không kiểm được bằng validator (giá trị giả trùng không gian với mã thật). (c) Phần chép lại nội dung ảnh (`transcript`) do eval-qa tự đọc, chưa có người thứ hai đối chiếu.

**Sự cố ghi nhận.**
- *Đợt 2:* giữ nguyên email vai trò khiến bảng ánh xạ cũ còn 4 email đã bị đổi, lưới chặn rò rỉ báo và dừng dựng, giữ nguyên `dataset.jsonl` cũ. Đã xoá mục email cũ khỏi bảng ánh xạ và dựng lại.
- *Đợt 3:* (1) lưới chặn báo nhầm 44 giá trị vì tìm chuỗi con trong id/URL và vì mã giả 4 chữ số trùng mã thật khác → sửa thành khớp nguyên số, chỉ xét `text`/`transcript`, bỏ qua số trùng giá trị giả. (2) Bước che mã OTP bị `pii_mask` che lần hai, cho hai giá trị khác nhau cho cùng một mã → sửa không che hai lần. (3) **Duyệt tay phát hiện 3 mã OTP còn lộ** (l016–l018) vì regex loại nhầm số có dấu phẩy ngay sau ("…226999, hiệu lực…"); đã sửa và dựng lại, 3 mã thật nay là giá trị giả. (4) Quét độc lập phát hiện 2 tin còn ID Zalo 20+ chữ số (`pii_mask` bỏ qua) → thêm quy tắc và kiểm tra ở validator. Không có giá trị thật nào vào repo; mọi lần dừng đều trước khi ghi file.

## 6. Nhãn thứ hai (blind20)

`eval/blind20.csv`: 20 mẫu đầu theo **thứ tự thu thập** (s001–s016, l001–l004), xáo thứ tự bằng seed cố định, **không kèm nhãn**. Chỉ có `blind_id` (b01–b20), kênh, văn bản, đường dẫn ảnh. Ảnh đã chép sang `eval/blind20/bNN.png` (tên trung tính) vì tên `sNNN`/`lNNN` lộ nhãn; không có `transcript`, tag, nguồn. Bảng đối chiếu `eval/blind20.key.csv` chỉ có `blind_id → id`, nhưng chữ đầu của `id` (`s`/`l`) cho biết nhãn: **người gán không mở file này trước khi điền xong**. Đợt 3 **không đổi** 20 mẫu này; 70 mẫu vsms chưa có người gán nhãn thứ hai (đề xuất đợt sau lấy 20 mẫu trong số đó, chọn ngẫu nhiên).

Cột người gán điền: `label (scam|legit)`, `group`, `scenario_id`, `chac_chan (y|n)`, `ghi_chu`. Điền xong chạy:

```bash
python3 eval/tools/compare_blind20.py          # đồng thuận nhãn, kappa, danh sách mẫu lệch
```

Lưu ý: tỷ lệ scam/legit của 20 mẫu này không cân bằng (do thứ tự thu thập; số cụ thể xem ở `eval/blind20.key.csv` **sau khi gán xong**), và 6 ảnh có dấu X/"GIẢ MẠO" nên tự lộ đáp án; kết quả đồng thuận vì thế có thể cao hơn thực tế. Mẫu lệch → ghi `docs/DECISIONS.md` và hỏi PM, **không sửa nhãn** (quy tắc eval-qa). Xong việc có thể xoá `eval/blind20/` để repo nhẹ.

## 7. Kiểm tra và công cụ

```bash
python3 eval/tools/validate_dataset.py eval/dataset.jsonl --min-total 100 --min-images 20 --min-g17 2 --min-per-group 10 --max-source dataset-pham-lehong=25 --max-synthetic 5
# kết quả hiện tại: FAIL 3 cổng (ảnh thật 17/20, G2 thật 9/10, G5 thật 8/10); các cổng khác đạt
python3 eval/tools/validate_dataset.py eval/pool/pham-lehong-ads.jsonl --pool
python3 eval/tools/validate_raw_pool.py eval/pool/vsms_train.jsonl eval/pool/vsms_test.jsonl --main eval/dataset.jsonl
python3 eval/tools/recall_by_tag.py eval/reports/<stamp>-<tag>.json --data eval/dataset.jsonl   # recall riêng: ảnh annotated / không chú thích / official_mock / injection / template_like / provenance / scenario
python3 eval/tools/compare_blind20.py
```

`validate_dataset.py` kiểm tra: đủ trường và đúng kiểu, `id` không trùng, file ảnh tồn tại và là PNG/JPEG thật ≤ 5 MB, mẫu ảnh có `text` rỗng và `transcript`, mẫu thật có `synthetic=false` + `source_url`, mẫu tổng hợp chỉ cho `injection` và có trần `--max-synthetic`, `source_date` hợp lệ, không trùng văn bản/ảnh, **không có hai mẫu văn bản gần trùng (Jaccard từ ≥ 0,85)**, không còn SĐT/STK/email cá nhân/biển số/handle/OTP/ID Zalo thật (chạy `pii_mask` và các regex bổ sung lên `text` và `transcript`), không có `ambiguous` trong tập chính. `--min-images` chỉ đếm ảnh **không phải** `official_mock`; `--min-per-group` chỉ đếm scam **thật** (không tính mẫu tổng hợp).

`validate_raw_pool.py` kiểm tra pool nhãn thô: đủ trường, `raw_label` ∈ {0, 1, null} (null ⇔ cờ `label_conflict`), `split` khớp tên file, id/văn bản không trùng, **không giao với tập chính**, cùng bộ kiểm tra PII. Nhãn trong pool là **nhãn thô của tác giả, không dùng để chấm điểm**.

## 8. Hiện trạng so với mục tiêu (2026-11-26, sau đợt 3)

| Hạng mục | Hiện có | Mục tiêu | Thiếu / ghi chú |
|---|---|---|---|
| Tổng mẫu chính | 107 | 100 | đã đạt, nhưng 79/107 (74%) từ bộ dữ liệu công khai, trong đó 70 từ một nguồn (vietnamese_sms_dataset) |
| Ảnh thật (không `official_mock`) | 17 | 20 | **thiếu 3** (đợt này không quét báo) |
| G1.7 (mẫu thật) | 4 (s002, s007, s016, s017) | 2 | đã đạt; mới có 1 mẫu "báo cấp cứu" (s017), 3 mẫu còn lại là "đóng học phí" |
| Scam THẬT G1 / G2 / G3 / G4 / G5 | 24 / 9 / 10 / 10 / 8 | ≥ 10 mỗi nhóm | **G2 thiếu 1, G5 thiếu 2**. Cổng chỉ tính mẫu thật; cộng 5 mẫu injection tổng hợp (mỗi nhóm 1) thì là 25 / 10 / 11 / 11 / 9. Trong số mẫu thật, template_like: G1=2, G2=5, G3=1, G4=3, G5=2 (cả 5 mẫu vsms của G2 đều template_like) |
| legit / hard_negative | 41 / 35 | 20 / 15 | đã đạt; thiếu tin đời thường giữa người với người |
| injection | 5 (tổng hợp) | 5 | đạt, nhưng 100% tổng hợp, chưa có người duyệt |
| Mẫu tổng hợp trên tổng | 5/107 = 4,7% | — | báo trên slide |
| `template_like` | 13 mẫu scam | — | báo recall riêng |
| Kênh | `sms` chiếm phần lớn văn bản; chưa có tin Zalo/Messenger dạng văn bản từ nguồn công khai | — | tin Zalo/Messenger chủ yếu ở dạng ảnh |

**Rủi ro đã biết khi báo cáo số liệu:** (1) tập trung nguồn và thời gian (mục 2, phát hiện 2); (2) ~13 mẫu có khuôn mẫu nghi sinh tự động; (3) nhãn 70 mẫu vsms do một người gán; (4) tỷ lệ nhãn sai của vietnamese_sms_dataset chưa biết; (5) mọi mẫu vsms là SMS, không đại diện cho Zalo/Messenger.
