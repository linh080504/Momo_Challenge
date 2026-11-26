# Bộ kit "đội AI" cho dự án Trước Khi Chuyển

Bộ kit biến Claude Code thành một đội 7 thành viên AI có vai rõ ràng, 9 skill chuyên môn và các "hàng rào" an toàn, dùng chung cho cả đội qua git. Mỗi người trong đội lái một agent đúng vai của mình; PM điều phối bằng kế hoạch 14 ngày ở `docs/PLAN.md`.

## Chạy MVP trên máy

Cần Python 3.12+ và Node.js 24. OCR tiếng Việt và đọc QR chạy cục bộ. SQLite dùng cho máy phát triển. Bản public dùng migration PostgreSQL/Supabase.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r apps/api/requirements-dev.txt
npm.cmd ci --prefix apps/api/tools/media
npm.cmd ci --prefix apps/web
.\.venv\Scripts\python.exe infra/setup_local.py
```

Mở hai terminal ở gốc repo và chạy mỗi lệnh trong một terminal. Trên macOS/Linux dùng `python3`, `.venv/bin/python` và `npm`.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --no-access-log
npm.cmd run dev --prefix apps/web
```

- Web tại **http://localhost:3000**, API docs tại **http://localhost:8000/docs**, bàn vận hành tại **http://localhost:3000/ops**.
- Hai tài khoản demo local có trong `.env` vừa tạo. Đăng nhập vai người dùng để báo cáo. Đăng nhập vai vận hành trong cửa sổ riêng để duyệt. Kiểm tra lại nội dung trùng số tài khoản, số điện thoại hoặc tên miền để thấy cảnh báo đã xác nhận.
- Có thể dùng `docker compose up --build` sau khi tạo `.env`. Compose chạy API và web trên máy, lưu DB trong volume riêng.
- Đặt `LLM_BASE_URL` (tới gốc API tương thích Chat Completions, thường kết thúc bằng `/v1`), `LLM_API_KEY`, `LLM_MODEL`, `LLM_FALLBACK_MODEL` và `SAFE_BROWSING_KEY` nếu có tài khoản dịch vụ. Chế độ hạn chế dùng luật và dữ liệu nội bộ. Google Safe Browsing chỉ đối chiếu tên miền gốc, với độ phủ giới hạn theo tên miền.

### Kiểm tra và triển khai

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd run build --prefix apps/web
.\.venv\Scripts\python.exe eval/prepare_smoke.py
.\.venv\Scripts\python.exe .claude/skills/eval-harness/scripts/run_eval.py --data eval/generated/dataset.smoke.jsonl --endpoint http://localhost:8000/v1/analyze --tag smoke-local --out eval/generated/reports
```

Tập smoke có văn bản và ảnh **tổng hợp**. Các mẫu này dùng để kiểm tra kết nối API và OCR. [Quy trình eval](eval/README.md) · [Triển khai public và smoke test](infra/deploy/README.md) · [Kịch bản thử cho BGK](submission/guide/HUONG_DAN.md)

## 1. Bộ kit gồm gì

```
CLAUDE.md                     bộ nhớ dự án: mục tiêu, luật không được phá, lệnh, quy ước
.mcp.json                     playwright (chụp/kiểm giao diện); context7 do mỗi người cài bằng `npx ctx7 setup --claude`
.claude/settings.json         quyền mặc định + 3 hook
.claude/hooks/                protect-files · format-on-save · session-context
.claude/agents/               7 agent (xem bảng dưới)
.claude/skills/               9 skill (xem bảng dưới), có script chạy được
docs/                         PLAN (14 ngày) · PRODUCT_BRIEF · STATUS · DECISIONS · USER_TESTS
eval/dataset.example.jsonl    18 mẫu TỔNG HỢP để chạy thử eval
tests/test_kit_scripts.py     test cho các script trong kit
```

### Đội agent

| Agent | Vai | Model | Sở hữu thư mục | Skill nạp sẵn |
|---|---|---|---|---|
| `pm-lead` | Chia việc, bám đề, cắt phạm vi, nhật ký | inherit | `docs/**` | — (đọc gate-check, daily-standup) |
| `ai-engineer` | Pipeline AI, prompt, điểm lai, gom chiến dịch | opus | `apps/api/app/analyzer/**`, `evidence/**`, `prompts/**` | scam-analyzer, pii-guard, evidence-tools, eval-harness |
| `backend-engineer` | API, DB, auth, ops API, Telegram, VietQR, deploy | sonnet | `apps/api/**` (trừ analyzer), `infra/**` | vietqr, pii-guard |
| `frontend-engineer` | Web người dùng + bàn làm việc `/ops` | sonnet | `apps/web/**` | — |
| `eval-qa` | Dữ liệu eval, chạy eval, thử như BGK, e2e | sonnet | `eval/**`, `tests/e2e/**` | eval-harness, scam-analyzer, pii-guard |
| `security-reviewer` | Rà bảo mật, PII, tuân thủ (chỉ đọc) | opus | — | pii-guard |
| `pitch-writer` | PDF 1 trang, README nộp, slide, video, Q&A | sonnet | `submission/**` | — (đọc submission-pack) |

### Skills

| Skill | Kích hoạt | Dùng để |
|---|---|---|
| `scam-analyzer` | Tự động | Hợp đồng pipeline, schema JSON, taxonomy 5 nhóm, prompt mẫu, điểm lai |
| `eval-harness` | Tự động hoặc `/eval-harness` | Chạy eval, cổng chất lượng, hướng dẫn xây dữ liệu |
| `vietqr` | Tự động | Đọc/tạo/kiểm tra VietQR (script có test CRC) |
| `evidence-tools` | Tự động | Kiểm tra tên miền nhái, Safe Browsing, RDAP, danh sách đen |
| `pii-guard` | Tự động | Ẩn danh trước khi gọi LLM, quy tắc dữ liệu, Luật AI/BVDLCN |
| `deploy-runbook` | `/deploy-runbook setup\|deploy\|smoke <url>\|rollback` | Deploy, smoke test, giám sát, rollback |
| `submission-pack` | `/submission-pack guide\|readme\|slides\|video\|check` | 4 thành phần bài nộp + checklist cuối |
| `daily-standup` | `/daily-standup <ngày>` | Tổng hợp commit, so với PLAN, ghi STATUS |
| `gate-check` | `/gate-check G0\|G1\|G2\|G3` | Kiểm cổng bằng bằng chứng, chạy trong subagent riêng |

Skill "gọi tay" đặt `disable-model-invocation: true` để Claude không tự deploy hay tự nộp bài.

### Cấu trúc mã nguồn MVP

Cấu trúc dưới đây bám theo [Product Brief](docs/PRODUCT_BRIEF.md), [kế hoạch 14 ngày](docs/PLAN.md) và [hợp đồng ngày 2](docs/TASKS.md#hợp-đồng-nối-việc-ngày-2-chốt-trước-1000-đổi-phải-ghi-decisions). Các thư mục chứa tài sản của đội có thể bắt đầu từ `.gitkeep`.

| Đường dẫn | Nội dung dự kiến | Chủ trì |
|---|---|---|
| `apps/web/app/(public)/` · `apps/web/components/analysis/` | Next.js cho người dùng. Một ô nhập văn bản hoặc ảnh, nén ảnh, tiến trình xử lý, thẻ kết quả có trích dẫn và nút báo cáo. | FE |
| `apps/web/app/login/` · `apps/web/app/ops/[campaignId]/` · `apps/web/components/ops/` | Đăng nhập vai người dùng và vận hành. Hàng chờ tại `/ops`, chi tiết chiến dịch, bằng chứng, duyệt hoặc bác bỏ và lịch sử. | FE |
| `apps/web/app/qr/` · `apps/web/app/share/[token]/` | Hai mục Should. Kiểm tra VietQR và xem tóm tắt đã che dữ liệu cá nhân qua link chia sẻ hết hạn sau 24 giờ. | FE |
| `apps/web/lib/` · `apps/web/public/` | Client gọi API, kiểu dữ liệu giao diện, tiện ích xử lý ảnh và tài nguyên tĩnh. | FE |
| `apps/api/app/api/` · `apps/api/app/schemas/` | FastAPI cho health check, phân tích, báo cáo, vận hành, QR và chia sẻ. Nhận ảnh PNG/JPEG qua JSON base64, tối đa 5 MB byte gốc. Kiểm tra đầu vào và đầu ra theo hợp đồng. | BE |
| `apps/api/app/analyzer/{agents,pipeline,providers}/` | Nơi xây agent chạy trong sản phẩm, pipeline đọc ảnh → trích thực thể → che dữ liệu → tra bằng chứng → suy luận → chấm điểm và hậu kiểm. Adapter cho OCR, model chính và dự phòng. | AI |
| `apps/api/app/evidence/` · `apps/api/app/privacy/` | Kiểm tra tên miền, Google Safe Browsing và danh sách nội bộ đã duyệt. Che dữ liệu cá nhân trước khi chuyển ra ngoài, chuẩn hóa thực thể và kiểm soát dữ liệu lưu. | AI · BE |
| `apps/api/app/{reports,ops,auth,db}/` | Nhận báo cáo, gom theo tài khoản, số điện thoại hoặc tên miền, tạo hồ sơ chiến dịch, phân quyền và ghi nhật ký duyệt. Cảnh báo đã xác nhận xuất hiện khi người dùng kiểm tra lại đầu vào liên quan sau khi chuyên viên duyệt. | BE · AI |
| `apps/api/app/{qr,sharing}/` | Đọc và đối chiếu VietQR, tạo lại QR sau khi người dùng xác nhận người nhận, tạo link chia sẻ có thời hạn. | BE |
| `prompts/` · `.claude/skills/scam-analyzer/` | Prompt có phiên bản, taxonomy và JSON Schema dùng chung cho API, web và eval. | AI |
| `eval/` · `eval/images/` · `eval/reports/` | Dữ liệu JSONL, ảnh test đã ẩn danh và báo cáo. `dataset.example.jsonl` có mẫu tổng hợp. `dataset.jsonl` dành cho tập đánh giá của đội. `holdout.jsonl` do QA giữ riêng. | QA |
| `apps/api/tests/` · `tests/e2e/` · `.github/workflows/` | Test API, kiểm thử luồng ảnh → kết quả → báo cáo → duyệt → cảnh báo, và CI. | BE · QA |
| `infra/docker/` · `infra/supabase/migrations/` · `infra/deploy/{api,web}/` | Vị trí cho cấu hình container, migration PostgreSQL/Supabase và triển khai API với web public. Quy trình smoke test và rollback nằm trong skill `deploy-runbook`. | BE |
| `docs/` · `submission/{guide,source,slides,video}/` | Kế hoạch, nhật ký, kiểm thử người dùng và bốn thành phần bài nộp theo mẫu đã có. | PM · pitch-writer |

Agent trong `.claude/agents/` hỗ trợ đội phát triển. Agent trong `apps/api/app/analyzer/agents/` thuộc mã chạy của sản phẩm. Vòng MVP ưu tiên ảnh và văn bản, bao gồm URL cần kiểm tra. Ghi âm, bảng tổng quan và cảnh báo qua email/SMS thuộc phần mở rộng trong [PLAN](docs/PLAN.md#hạng-mục-mở-rộng).

## 2. Cài đặt (khoảng 10 phút)

Cần: Claude Code bản mới, Git, Python ≥ 3.10, `jq` (hook dùng), Node.js ≥ 22.13 (cho `ctx7`).

```bash
# 1. Tạo repo và chép nội dung bộ kit vào GỐC repo
mkdir truoc-khi-chuyen && cd truoc-khi-chuyen && git init
cp -r /duong-dan/truoc-khi-chuyen-kit/. .
chmod +x .claude/hooks/*.sh

# 2. Kiểm tra script
python3 tests/test_kit_scripts.py
python3 .claude/skills/eval-harness/scripts/run_eval.py --data eval/dataset.example.jsonl --baseline --tag baseline

# 3. Commit đầu tiên (skill /daily-standup đọc git log nên cần ít nhất 1 commit)
git add . && git commit -m "chore: add AI team kit"

# 4. Context7 — MỖI thành viên chạy, khi được hỏi chọn "MCP server"
npx ctx7 setup --claude
claude mcp list                  # phải thấy context7 ở trạng thái connected

# 5. Mở Claude Code
claude
```

Vì sao chọn "MCP server" chứ không phải "CLI + Skills": các agent trong kit khai báo danh sách công cụ cố định và đã được cấp `mcp__context7__*`, nên gọi được Context7 trực tiếp. Lựa chọn CLI + Skills cần thêm công cụ `Skill` vào từng agent.

Trong Claude Code:
- Duyệt MCP server `playwright` của dự án khi được hỏi.
- Kiểm tra agent: từ Claude Code v2.1.198, lệnh `/agents` không còn mở trình quản lý mà chỉ nhắc sửa file trong `.claude/agents/`. Hãy gõ `@` trong ô chat để thấy các mục "(agent)", hoặc hỏi: `Liệt kê các subagent của dự án và công cụ của từng agent.`
- Gõ `/` để thấy các skill; `/context` để chắc CLAUDE.md đã nạp.
- Thử: `Dùng subagent eval-qa chạy eval baseline trên eval/dataset.example.jsonl và giải thích vì sao baseline chưa đạt cổng.`

Nếu chưa thấy agent: khởi động lại Claude Code (lần đầu tạo thư mục `.claude/agents/` cần restart).

Windows: hook của kit là script bash dùng `jq`. Nếu thấy lỗi `jq: command not found`, cài bằng `winget install jqlang.jq` rồi mở lại terminal.

## 3. Ba cách dùng đội AI

### A. Mỗi người một vai — cách chính
Mỗi thành viên làm trên một git worktree riêng và chạy cả phiên bằng agent của vai mình:

```bash
git worktree add ../tkc-ai -b feat/ai-analyzer
cd ../tkc-ai && claude --agent ai-engineer
```

Phiên đó dùng system prompt, công cụ, model và skill nạp sẵn của agent. Ranh giới thư mục trong từng agent giúp 5 người không sửa đè nhau; mọi thứ vào `main` qua PR.

### B. Ủy quyền cho subagent trong một phiên
Dùng khi cần một góc nhìn tách biệt mà không làm đầy ngữ cảnh phiên chính:
- `Dùng subagent security-reviewer rà diff của nhánh này so với main.`
- `@agent-eval-qa tạo 10 đầu vào kiểu BGK chưa có trong eval và chạy qua API public.`

Mẫu "người viết / người duyệt": một phiên viết code, một subagent ở ngữ cảnh mới duyệt — người duyệt không thiên vị code mình vừa viết.

### C. Agent team (thử nghiệm) — cho rà soát song song
Bật riêng trên máy bạn, không commit: tạo `.claude/settings.local.json`

```json
{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }
```

Prompt mẫu (ngày 10, trước G2):

```text
Tạo agent team 3 teammate để rà bản public https://<url> trước feature freeze:
- "sec" dùng agent type security-reviewer
- "qa" dùng agent type eval-qa
- "pitch" dùng agent type pitch-writer (đối chiếu slide với tính năng đang chạy)
Mỗi người ghi vào file riêng trong docs/review-G2/, nhắn nhau để bỏ phát hiện trùng.
Chờ cả 3 xong rồi tổng hợp thành danh sách việc theo mức độ.
```

Lưu ý: tốn token gấp nhiều lần (mỗi teammate là một phiên riêng); bắt đầu với 3 teammate; không cho 2 teammate sửa cùng một file; teammate không áp dụng trường `skills` của agent (vẫn nạp skill của dự án như bình thường); không khôi phục được teammate khi `/resume`. Rà xong thì đặt biến về `0`, vì khi bật, subagent được đặt tên sẽ chạy thành teammate.

## 4. Lệnh nhanh

| Khi nào | Lệnh |
|---|---|
| 9:00 mỗi ngày | `/daily-standup 5` |
| Cuối ngày 1, 7, 10, 13 | `/gate-check G1` |
| Sau mỗi lần sửa prompt/model | `/eval-harness https://api.../v1/analyze v3-prompt` |
| Sau deploy | `/deploy-runbook smoke https://api...` |
| Ngày 11–12 | `/submission-pack slides` … `/submission-pack check` |

## 5. Hook đang bật

| Hook | Sự kiện | Làm gì |
|---|---|---|
| `protect-files.sh` | Trước Edit/Write | Chặn sửa `.env*` (trừ `.env.example`), `.git/`, `secrets/`, `eval/raw/`, `eval/holdout.jsonl` |
| `format-on-save.sh` | Sau Edit/Write | Format bằng ruff/prettier nếu đã cài; không bao giờ chặn |
| `session-context.sh` | Sau khi nén hội thoại | Nhắc lại luật dự án, 15 dòng cuối STATUS, eval gần nhất |

Quyền: cho phép sẵn các lệnh test/eval/git chỉ đọc; chặn đọc `.env`, `secrets/`, `eval/raw/` và `git push --force`.

## 6. Mẹo dùng hiệu quả

- Luôn cho Claude một cách tự kiểm: test, eval, smoke test, ảnh chụp giao diện. Yêu cầu dán bằng chứng, không nhận câu "đã xong".
- Việc nhiều file: bật plan mode (Shift+Tab) để Claude đọc và lập kế hoạch trước khi sửa.
- `/clear` giữa hai việc không liên quan; sửa sai 2 lần vẫn hỏng thì `/clear` và viết lại yêu cầu rõ hơn.
- Giữ CLAUDE.md ngắn; quy trình dài đưa vào skill.
- Thêm "use context7" khi hỏi về thư viện để lấy tài liệu đúng phiên bản.

## 7. Tùy chỉnh

- Đổi model một agent: sửa `model:` (`sonnet`, `opus`, `haiku`, `inherit`).
- Thêm skill: `.claude/skills/<ten>/SKILL.md`, phần `description` nói rõ khi nào dùng; giữ SKILL.md dưới 500 dòng, chi tiết để file phụ.
- Taxonomy: khi tìm được danh sách 25 kịch bản gốc, cập nhật `.claude/skills/scam-analyzer/taxonomy.md` và thêm mẫu eval tương ứng.

## 8. Tài liệu tham khảo

- Claude Code — Subagents: https://code.claude.com/docs/en/sub-agents
- Claude Code — Skills: https://code.claude.com/docs/en/skills
- Claude Code — Agent teams: https://code.claude.com/docs/en/agent-teams
- Claude Code — Hooks: https://code.claude.com/docs/en/hooks-guide
- Claude Code — MCP: https://code.claude.com/docs/en/mcp
- Claude Code — Permissions: https://code.claude.com/docs/en/permissions
- Claude Code — Best practices: https://code.claude.com/docs/en/best-practices
- Anthropic — Equipping agents for the real world with Agent Skills: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Anthropic — Building effective agents: https://www.anthropic.com/engineering/building-effective-agents
- Anthropic — Demystifying evals for AI agents: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Context7: https://github.com/upstash/context7
- PhoWhisper (VinAI): https://github.com/VinAIResearch/PhoWhisper
- Google Safe Browsing Lookup API v4: https://developers.google.com/safe-browsing/v4/lookup-api
