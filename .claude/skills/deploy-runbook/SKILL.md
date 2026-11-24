---
name: deploy-runbook
description: "Quy trình deploy và giữ sản phẩm chạy ổn định cho BGK — web lên Vercel, API lên Cloud Run/Railway/Fly.io (Singapore, luôn giữ 1 instance), biến môi trường, health check, smoke test, giám sát uptime, hạn mức chi phí LLM, rollback. Chỉ chạy khi được gọi /deploy-runbook."
disable-model-invocation: true
argument-hint: "[setup | deploy | smoke <base-url> | rollback]"
allowed-tools: Bash(bash .claude/skills/deploy-runbook/scripts/smoke_test.sh *)
---

# Deploy runbook

Yêu cầu: `$ARGUMENTS`. Nếu trống, hỏi người dùng muốn làm bước nào.

## setup (làm một lần, ngày 1–2)

1. Repo GitHub, nhánh `main` được bảo vệ; mỗi người làm trên nhánh riêng, merge qua PR.
2. **Web (Next.js)** → Vercel: import repo, root `apps/web`, đặt `NEXT_PUBLIC_API_URL`.
3. **API (FastAPI)** → chọn một: Cloud Run (`--min-instances=1 --region=asia-southeast1`), Railway hoặc Fly.io (`min_machines_running = 1`, region `sin`). Mục tiêu: không bị cold start khi BGK mở lần đầu.
4. **DB** → Supabase (Postgres + pgvector + Auth + Storage), region Singapore.
5. **Biến môi trường** (không commit; có `.env.example`): `LLM_API_KEY`, `LLM_MODEL`, `LLM_FALLBACK_MODEL`, `SAFE_BROWSING_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `TELEGRAM_BOT_TOKEN`, `ALLOWED_ORIGINS`.
6. Endpoint bắt buộc: `GET /health` (trả `{"status":"ok","version":...}`), `POST /v1/analyze`.
7. Giám sát: UptimeRobot (hoặc tương đương) ping `/health` 5 phút/lần, báo về nhóm chat của đội; Sentry cho lỗi; Langfuse cho trace LLM.
8. **Hạn mức chi phí**: đặt budget alert ở nhà cung cấp LLM; cache kết quả theo hash đầu vào; rate limit theo IP/người dùng.

## deploy

1. Chạy test và eval: `python3 tests/test_kit_scripts.py`, `/eval-harness`.
2. Merge vào `main` → CI deploy. Ghi version (git sha) vào `/health`.
3. Chạy smoke test trên URL public (bên dưới). Không đạt → rollback ngay.
4. Ghi vào `docs/STATUS.md`: version, thời gian, kết quả smoke.

## smoke

```bash
bash .claude/skills/deploy-runbook/scripts/smoke_test.sh https://api.ten-mien-cua-doi.vn
```

Kiểm tra: `/health` 200, `/v1/analyze` với 1 tin lừa đảo và 1 tin hợp lệ trả đúng mức, thời gian < 8 giây.

## rollback

- Vercel: "Promote to Production" bản trước. Cloud Run: chuyển 100% traffic về revision trước. Railway/Fly: redeploy image trước.
- Sau rollback: chạy lại smoke, ghi sự cố vào `docs/STATUS.md`.

## Tuần chấm điểm

- Đóng băng deploy (chỉ hotfix có PM duyệt). Một người trực theo ca, có quyền rollback.
- Kiểm tra quota LLM mỗi sáng. Tài khoản test của BGK không bị rate limit chặn.
