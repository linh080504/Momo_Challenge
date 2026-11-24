#!/bin/bash
# SessionStart (compact): nhắc lại bối cảnh quan trọng sau khi Claude tự nén hội thoại.
# Mọi thứ in ra stdout được đưa vào ngữ cảnh của Claude.
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
echo "Nhắc bối cảnh dự án Trước Khi Chuyển:"
echo "- Hợp đồng đầu ra: .claude/skills/scam-analyzer/analysis.schema.json. Ẩn danh trước khi gọi LLM. Con người duyệt bước rủi ro."
echo "- Cổng: G0 ngày 1, G1 ngày 7, G2 ngày 10 (feature freeze), G3 ngày 13 (nộp). Kế hoạch: docs/PLAN.md"
if [ -f docs/STATUS.md ]; then
  echo "- 15 dòng cuối docs/STATUS.md:"
  tail -n 15 docs/STATUS.md
fi
if [ -f eval/reports/latest.json ]; then
  echo "- Eval đạt gần nhất:"
  jq -c '{tag, recall_scam, false_positive_rate, p95_text, p95_image, time}' eval/reports/latest.json 2>/dev/null
fi
exit 0
