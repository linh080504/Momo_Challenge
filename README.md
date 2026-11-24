# Bộ kit "đội AI" cho dự án Trước Khi Chuyển

Bộ kit biến Claude Code thành một đội 7 thành viên AI có vai rõ ràng, 9 skill chuyên môn và các "hàng rào" an toàn, dùng chung cho cả đội qua git. Mỗi người trong đội lái một agent đúng vai của mình; PM điều phối bằng kế hoạch 14 ngày ở `docs/PLAN.md`.

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
