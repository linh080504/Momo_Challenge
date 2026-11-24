#!/bin/bash
# PreToolUse (Edit|Write): chặn Claude sửa file nhạy cảm. Exit 2 = chặn và báo lý do cho Claude.
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
FILE_PATH="${FILE_PATH//\\//}"
BASENAME=$(basename "$FILE_PATH")

# .env.example được phép sửa; mọi .env khác bị chặn
if [[ "$BASENAME" == ".env.example" ]]; then exit 0; fi

PROTECTED_PATTERNS=("/.env" ".git/" "/secrets/" "/eval/raw/" "eval/holdout.jsonl" "package-lock.json")
for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "Bị chặn: $FILE_PATH thuộc vùng bảo vệ ('$pattern'). Secret, dữ liệu thô chưa ẩn danh và holdout eval do con người quản lý." >&2
    exit 2
  fi
done
exit 0
