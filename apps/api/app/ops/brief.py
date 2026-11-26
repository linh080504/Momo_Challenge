GROUPS = {
    "G1": "Mạo danh cơ quan, tổ chức", "G2": "Mạo danh người quen",
    "G3": "Đầu tư hoặc tuyển dụng", "G4": "Mua bán và giao dịch trực tuyến",
    "G5": "Đánh cắp dữ liệu hoặc tài khoản",
}


def brief(campaign):
    name = GROUPS.get(campaign["group"], "Cần xác minh")
    count = campaign["report_count"]
    title = f"{name} · {count} báo cáo"
    if campaign["signals"]:
        summary = f"Nhóm {name.lower()} có {count} báo cáo. Tín hiệu đã ghi nhận: {campaign['signals'][0]}"
    else:
        summary = f"Có {count} báo cáo trong hồ sơ. Hãy xem thông tin đối chiếu trước khi quyết định."
    return {"title": title, "summary": summary}
