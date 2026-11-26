# Điểm nguy cơ lai (luật + LLM)

`rule_score` (0–100, code tính, cộng dồn rồi cắt 0–100). Bảng khớp `rules_v1` (`apps/api/app/analyzer/rules.py`, `scoring.py`). Dòng có ★ là dòng thêm ngày 2026-11-26 (DECISIONS cùng ngày), **chưa có số eval** đo tác động.

| Tín hiệu | Điểm |
|---|---|
| Số tài khoản/SĐT/tên miền có trong danh sách đen ĐÃ DUYỆT | +60 |
| ★ Tên miền có trong danh sách đen cộng đồng bên thứ ba (evidence `external_blacklist`, chưa qua duyệt; một mình ra `medium`) | +45 |
| Safe Browsing báo nguy hiểm | +60 |
| `domain_check` level high / medium (chỉ tính URL xấu nhất, một lần) | +45 / +20 |
| Tự xưng cơ quan nhà nước + yêu cầu chuyển tiền vào tài khoản cá nhân | +40 |
| Yêu cầu OTP, mật khẩu, mã xác thực | +50 |
| Yêu cầu cài app ngoài kho (link .apk) | +45 |
| QR có CRC sai, hoặc người nhận trong QR khác người được nhắc tới | +35 |
| Có từ khóa gấp/dọa/giữ bí mật (mỗi loại) | +10 |
| ★ Có câu ra lệnh cho máy kiểm tra (prompt injection): "câu ra lệnh cho AI" tự nó là dấu hiệu lừa đảo | +35 |
| ★ Khớp mẫu đặc trưng của 1 trong 25 mã taxonomy (tính một lần; riêng G5.1 +20, G5.3 +45) | +35 |
| ★ Đòi chuyển/nộp/nạp tiền (bỏ qua câu kể lại "bạn vừa chuyển…"; không cộng nếu đã có dòng +40 hoặc +10 bên dưới) | +10 |
| ★ Bảo chuyển vào tài khoản cá nhân/người khác, không kèm tự xưng cơ quan | +10 |
| Tên miền chính thức khớp danh sách trắng **hoặc có đuôi `.gov.vn`** (một lần; chỉ khi không có URL rủi ro hay danh sách đen) | −30 |

`llm_score`: ánh xạ `risk_level` của LLM → high 80, medium 50, uncertain 30, low 15.

Trộn (lệch nhau thì lấy mức cao hơn):

```python
final = max(rule_score, llm_score)
if final >= 60:            level = "high"      # rule_score ≥ 60 luôn ra high, bất kể LLM
elif final >= 35:          level = "medium"
elif llm_level in ("uncertain", None):  # None = LLM lỗi/timeout
                           level = "uncertain"
else:                      level = "low"
```

Điều chỉnh trọng số chỉ dựa trên kết quả eval, ghi lý do vào `docs/DECISIONS.md`. Khi dùng `vietnamese_sms_dataset`: chỉ chỉnh luật trên `vsms_train`, số báo cáo lấy từ `vsms_test` (DECISIONS 2026-11-26).
