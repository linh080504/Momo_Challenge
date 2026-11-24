# Điểm nguy cơ lai (luật + LLM)

`rule_score` (0–100, code tính, cộng dồn rồi cắt 0–100):

| Tín hiệu | Điểm |
|---|---|
| Số tài khoản/SĐT/tên miền có trong danh sách đen ĐÃ DUYỆT | +60 |
| Safe Browsing báo nguy hiểm | +60 |
| `domain_check` level high / medium | +45 / +20 |
| Tự xưng cơ quan nhà nước + yêu cầu chuyển tiền vào tài khoản cá nhân | +40 |
| Yêu cầu OTP, mật khẩu, mã xác thực | +50 |
| Yêu cầu cài app ngoài kho (link .apk) | +45 |
| QR có CRC sai, hoặc người nhận trong QR khác người được nhắc tới | +35 |
| Có từ khóa gấp/dọa/giữ bí mật (mỗi loại) | +10 |
| Tên miền chính thức khớp danh sách trắng | −30 |

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

Điều chỉnh trọng số chỉ dựa trên kết quả eval, ghi lý do vào `docs/DECISIONS.md`.
