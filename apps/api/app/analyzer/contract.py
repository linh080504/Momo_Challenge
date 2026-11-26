import json

from jsonschema import Draft202012Validator

from ..kit import SKILLS

DISCLAIMER = "Kết quả do AI phân tích và có thể sai. Hãy xác minh qua số tổng đài chính thức trước khi chuyển tiền."
SCHEMA = json.loads((SKILLS / "scam-analyzer" / "analysis.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)
LABELS = {
    "high": "Có dấu hiệu lừa đảo rõ ràng. Hãy tạm dừng và xác minh qua kênh chính thức.",
    "medium": "Có chi tiết đáng ngờ. Hãy kiểm tra lại người gửi trước khi chuyển tiền.",
    "uncertain": "Chưa đủ thông tin để kết luận. Hãy xác minh qua kênh chính thức.",
    "low": "Chưa thấy dấu hiệu lừa đảo, nhưng hãy xác minh qua kênh chính thức.",
}


class AnalyzerError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(message)
