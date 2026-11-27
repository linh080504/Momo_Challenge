from .brief import brief


def alert_preview(campaign):
    draft = brief(campaign)
    code = campaign["id"][:8].upper()
    published = (campaign["state"] == "approved" and
                 campaign["report_count"] > 0 and bool(campaign["entities"]))
    message = "Hãy dừng trước khi chuyển tiền và xác minh qua kênh chính thức."
    return {
        "campaign_id": campaign["id"],
        "revision": campaign["revision"],
        "approval": campaign["state"],
        "channels": [
            {"id": "web", "state": "published" if published else "preview", "title": draft["title"],
             "body": f"{draft['summary']} {message}"},
            {"id": "in_app", "state": "preview", "title": f"Kiểm tra chiến dịch {code}", "body": message},
            {"id": "email", "state": "preview", "title": f"Cảnh báo PayPause {code}", "body": message},
            {"id": "sms", "state": "preview", "title": "PayPause", "body": f"PayPause {code}. {message}"},
            {"id": "internal", "state": "preview", "title": f"Vận hành · {code}",
             "body": f"{draft['summary']} Đối chiếu bằng chứng và ghi kết quả vào hồ sơ."},
        ],
        "transaction_status": "unverified",
    }
