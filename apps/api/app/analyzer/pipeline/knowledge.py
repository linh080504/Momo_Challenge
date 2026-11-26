GUIDANCE = {
    "G1": "Xác minh yêu cầu qua số công khai của cơ quan hoặc đơn vị được nhắc đến.",
    "G2": "Liên lạc với người quen qua số cũ hoặc một kênh liên lạc đã biết.",
    "G3": "Xác minh đơn vị tuyển dụng hoặc đầu tư trước khi trả phí hay nạp tiền.",
    "G4": "Kiểm tra người nhận và lịch sử giao dịch trực tiếp trong ứng dụng ngân hàng.",
    "G5": "Tự mở ứng dụng chính thức. Giữ riêng mã xác thực và mật khẩu.",
}


def retrieve_guidance(matches, url_suspicious):
    groups = dict.fromkeys(rule.scenario.split(".")[0] for rule, _ in matches)
    if url_suspicious:
        groups.setdefault("G5", None)
    return [{"id": f"paypause-taxonomy-{group}", "text": GUIDANCE[group]} for group in list(groups)[:3]]
