// Kiểu dữ liệu khớp .claude/skills/scam-analyzer/analysis.schema.json.
// Giao diện CHỈ hiển thị những gì nằm trong JSON này. Không suy diễn mức nguy cơ ở client.

export const RISK_LEVELS = ["high", "medium", "low", "uncertain"] as const;
export type RiskLevel = (typeof RISK_LEVELS)[number];

export const RECOMMENDED_ACTIONS = [
  "stop_and_verify",
  "ask_guardian",
  "report",
  "proceed_with_clean_qr",
  "no_action",
] as const;
export type RecommendedAction = (typeof RECOMMENDED_ACTIONS)[number];

export type ScenarioGroup = "G1" | "G2" | "G3" | "G4" | "G5";

export type Tactic =
  | "urgency"
  | "authority"
  | "secrecy"
  | "greed"
  | "fear"
  | "personal_account"
  | "credential_request"
  | "app_install"
  | "link"
  | "other";

export type EntityType =
  | "ACCOUNT"
  | "PHONE"
  | "URL"
  | "EMAIL"
  | "CARD"
  | "AMOUNT"
  | "BANK"
  | "ORG";

export type EvidenceSource =
  | "internal_blacklist"
  | "safe_browsing"
  | "domain_check"
  | "rdap"
  | "vietqr"
  | "rules"
  | "llm";

export interface RedFlag {
  quote: string;
  reason: string;
  tactic?: Tactic;
}

export interface Entity {
  type?: EntityType;
  token?: string;
  /** Giá trị đã che bớt, ví dụ 0123****89. Đây là thứ DUY NHẤT được phép hiện ra màn hình. */
  display?: string;
}

export interface EvidenceItem {
  source: EvidenceSource;
  finding: string;
  weight?: number;
}

export interface Analysis {
  risk_level: RiskLevel;
  risk_score: number;
  scenario_group: ScenarioGroup | null;
  scenario_id?: string | null;
  summary: string;
  red_flags: RedFlag[];
  verification_questions: string[];
  recommended_action: RecommendedAction;
  entities?: Entity[];
  evidence: EvidenceItem[];
  ai_disclaimer: string;
  model?: string;
  prompt_version?: string;
  latency_ms?: number;
}

const isObject = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);

const isString = (v: unknown): v is string => typeof v === "string";

/**
 * Kiểm tra JSON từ máy chủ có đúng hình dạng schema không trước khi vẽ lên thẻ.
 * Sai hình dạng → trả null và giao diện báo lỗi, KHÔNG vẽ thẻ thiếu mảnh
 * (một thẻ thiếu mảnh dễ bị hiểu nhầm là "không có gì đáng ngờ").
 */
export function parseAnalysis(value: unknown): Analysis | null {
  if (!isObject(value)) return null;

  const { risk_level, recommended_action } = value;
  if (!RISK_LEVELS.includes(risk_level as RiskLevel)) return null;
  if (!RECOMMENDED_ACTIONS.includes(recommended_action as RecommendedAction)) return null;
  if (typeof value.risk_score !== "number") return null;
  if (!isString(value.summary) || !isString(value.ai_disclaimer)) return null;
  if (!Array.isArray(value.red_flags) || !Array.isArray(value.evidence)) return null;
  if (!Array.isArray(value.verification_questions)) return null;

  const redFlags = value.red_flags;
  if (!redFlags.every((f) => isObject(f) && isString(f.quote) && isString(f.reason))) return null;
  if (!value.verification_questions.every(isString)) return null;
  if (!value.evidence.every((e) => isObject(e) && isString(e.source) && isString(e.finding))) {
    return null;
  }
  if (value.entities !== undefined && !Array.isArray(value.entities)) return null;

  return value as unknown as Analysis;
}
