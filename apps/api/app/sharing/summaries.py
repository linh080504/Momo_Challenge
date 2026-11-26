from ..analyzer.contract import DISCLAIMER

SUMMARIES = {
    "high": "Có dấu hiệu lừa đảo rõ ràng. Hãy tạm dừng chuyển tiền và kiểm tra qua kênh chính thức.",
    "medium": "Nội dung có chi tiết đáng ngờ. Hãy hỏi thêm người thân và xác minh người gửi.",
    "uncertain": "Thông tin hiện có chưa đủ để kết luận. Hãy xác minh người gửi qua kênh chính thức.",
    "low": "Chưa thấy dấu hiệu lừa đảo rõ ràng. Vẫn hãy xác minh người nhận trước khi chuyển tiền.",
}


def summary_for(risk):
    return {"risk": risk, "summary": SUMMARIES[risk], "disclaimer": DISCLAIMER}
