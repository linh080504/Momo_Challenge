#!/bin/bash
# PostToolUse (Edit|Write): format file vừa sửa nếu có công cụ. Không bao giờ chặn (luôn exit 0).
FILE_PATH=$(jq -r '.tool_input.file_path // empty')
[ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ] && exit 0
case "$FILE_PATH" in
  *.py)
    command -v ruff >/dev/null 2>&1 && ruff format --quiet "$FILE_PATH" ;;
  *.ts|*.tsx|*.js|*.jsx|*.json|*.css|*.md)
    [ -x "$(command -v npx)" ] && [ -f "${CLAUDE_PROJECT_DIR:-.}/node_modules/.bin/prettier" ] && \
      npx --no-install prettier --write --log-level silent "$FILE_PATH" ;;
esac
exit 0
