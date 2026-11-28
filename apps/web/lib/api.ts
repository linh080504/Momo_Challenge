export const apiBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export type Risk = "high" | "medium" | "uncertain" | "low";
export type Entity = { type: string; display: string };
export type Region = [number, number, number, number];
export type UrlCheck = { host: string; level: "low" | "medium" | "high"; domain_age_days: number | null;
  domain_registered_on?: string | null; signals: string[]; official_brand?: string | null };
export type BrandVerdict = "BENIGN" | "ABSTAIN_NEEDS_REVIEW" | "IMPOSTOR";
export type BrandAssessment = { verdict: BrandVerdict; version: string; findings: string[] };
export type BrandAlert = { host: string; finding: string };
export type BrandSource = "CT_LOGS" | "CSKH_REPORT" | "QR_GATEWAY" | "THREAT_INTEL" | "QUICK_CHECK";
export type BrandCase = {
  host: string; state: CampaignState; revision: number; sources: Partial<Record<BrandSource, number>>;
  assessment: BrandAssessment; created: number; updated: number; expires: number | null;
};
export type WebsiteReport = {
  brand_review?: BrandAssessment & { source: "public_page" | "submitted_html" | "unavailable" };
  capture_scope?: "listed" | "unlisted";
  reputation?: Partial<Record<"virustotal" | "urlhaus" | "phishtank",
    { status: "match" | "clear" | "checked" | "unavailable"; scope: string }>>;
  public_page?: { status: "read" | "restricted" | "redirect" | "unsupported" | "unavailable" | "too_large" | "busy";
    model?: string | null; title?: string | null; capture_jpeg?: string | null; findings?: string[];
    checked_at?: number; explanation?: { label: string; finding: string; kind?: "article"; support?: string; source_url?: string }[] };
  sources: Record<"domain" | "community" | "approved_cases" | "safe_browsing" | "rdap", "match" | "clear" | "checked" | "unavailable">;
  source_limits?: Partial<Record<"safe_browsing" | "rdap", string>>;
  article?: { publisher: string; host: string; title: string; image_webp: string | null; capture_jpeg?: string | null; findings: string[];
    context: "educational" | "uncertain"; model: string | null };
  screenshot: { credential_labels: string[]; brands: { name: string; domain_matches: boolean }[] } | null;
  markup: { status: "checked" | "unreadable"; findings: string[] } | null;
};
export type DocumentEvidence = {
  ocr_boxes: Region[];
  recompression_regions: Region[];
  signals: { category: string; finding: string }[];
  transaction_status: "unverified";
  notice: string;
};
export type TransferIntent = "receive" | "pay";
export type TransferReview = {
  intent: TransferIntent;
  status: "conflict" | "payment" | "unreadable" | "invalid_crc" | "link" | "unsupported" | "unavailable";
  amount?: string | null;
  bank?: string | null;
  account?: string;
  quote?: string;
  quote_source?: "message" | "image";
};
export type Analysis = {
  analysis_id: string;
  risk_level: Risk;
  risk_score: number;
  scenario_group: string | null;
  summary: string;
  red_flags: { quote: string; reason: string }[];
  content_context?: { quote: string; reason: string }[];
  verification_questions: string[];
  evidence: { source: string; finding: string; weight: number }[];
  entities: Entity[];
  ai_disclaimer: string;
  degraded: boolean;
  model?: string;
  image_reader?: "qwen4-max" | "local_ocr" | "local_ocr_fallback";
  analysis_path?: "fast" | "deep";
  document?: DocumentEvidence;
  transfer_review?: TransferReview;
  brand_alert?: BrandAlert;
  url_checks?: UrlCheck[];
  website_report?: WebsiteReport;
  guidance?: { id: string; text: string; source_url?: string; version?: string }[];
};
export type AnalysisEvent = {
  stage: string;
  message: string;
  entities?: Entity[];
  website_capture?: { jpeg: string; host: string };
};
export type Input = {
  text: string;
  url?: string;
  website_html?: string;
  website_preview?: boolean;
  image_base64?: string;
  image_mime?: string;
  image_kind?: "image" | "receipt";
  qwen_vision?: boolean;
  audio_base64?: string;
  qr_payload?: string;
  transfer_intent?: TransferIntent;
};
export type Account = { email: string; role: "user" | "ops" };
export type Session = Account & { token: string };
export type CampaignState = "pending" | "approved" | "rejected";
export type SampleLabel = "scam" | "legit" | "uncertain" | "withdrawn";
export type SampleReview = { label: SampleLabel; revision: number; actor: string; created: number };
export type OpsSample = {
  id: string; created: number; risk: Risk; group: string | null; signals: string[];
  inputs: string[] | null; history: SampleReview[];
};
export type OpsOverview = { reports_24h: number; decisions_24h: number; pending: number; approved: number };
export type OpsSystem = {
  app_version: string;
  prompt_version: string;
  knowledge_version: string;
  qwen_model: string | null;
  safe_browsing_configured: boolean;
  reputation_configured: Record<"virustotal" | "urlhaus" | "phishtank" | "rdap", boolean>;
  speech_configured: boolean;
  website_read_enabled: boolean;
  website_capture_enabled: boolean;
};
export type CampaignAlerts = { transaction_status: "unverified"; channels: {
  id: "web" | "in_app" | "email" | "sms" | "internal"; state: "preview" | "published"; title: string; body: string;
}[] };
export type AgentReview = { status: "ok" | "quota" | "unavailable" | "invalid" | "disabled"; model: string | null; note: string | null };
export type Investigation = {
  nodes: { id: string; label: string; count: number | null }[];
  edges: { from: string; to: string; count: number | null; source?: "report_cooccurrence"; last_seen?: number | null }[];
  related_campaigns: { id: string; state: CampaignState; shared_entities: number }[];
  review?: AgentReview;
};
export type OpsWorkspace = {
  permission: "draft_only";
  supervisor_review?: AgentReview;
  detection: { risk: Risk; group: string | null; signals: string[]; source_counts: Record<string, number>; review?: AgentReview };
  threat_intel: { confirmed_related_campaigns: string[]; safe_browsing_hits: number; review?: AgentReview };
  forensics: { reviewed_input_counts: Record<string, number>; ocr_regions: number; jpeg_regions: number; transaction_status: "unverified"; review?: AgentReview };
  investigation: Investigation;
  protection: { recommendations: string[]; review?: AgentReview };
  report: { title: string; summary: string; recommendation: string; approval_required: true; status: "draft"; review?: AgentReview };
};
export type Campaign = {
  id: string;
  title: string;
  summary: string;
  state: CampaignState;
  risk: Risk;
  group: string | null;
  revision: number;
  report_count: number;
  entities: Record<string, number>;
  signals: string[];
  created: number;
  history: { actor: string; action: "approve" | "reject" | "edit_group" | "split_sample"; created: number }[];
  workspace?: OpsWorkspace;
  alerts?: CampaignAlerts;
};

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
  }
}

async function request(path: string, method = "GET", body?: object, token?: string, signal?: AbortSignal) {
  let response: Response;
  try {
    response = await fetch(apiBase + path, {
      method, body: body ? JSON.stringify(body) : undefined, signal, cache: "no-store",
      headers: {
        ...(body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: "Bearer " + token } : {}),
      },
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError("Chưa kết nối được với dịch vụ. Hãy thử lại sau.", 0);
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new ApiError(payload.detail || "Không thể hoàn tất yêu cầu. Hãy thử lại.", response.status);
  }
  return response;
}

export async function api<T>(path: string, method = "GET", body?: object, token?: string, signal?: AbortSignal) {
  return (await request(path, method, body, token, signal)).json() as Promise<T>;
}

export async function analyze(input: Input, update: (event: AnalysisEvent) => void, token: string | undefined, signal: AbortSignal) {
  const response = await request("/v1/analyze/stream", "POST", input, token, signal);
  if (!response.body) throw new Error("Không nhận được kết quả phân tích.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: Analysis | undefined;
  function accept(line: string) {
    if (!line.trim()) return;
    const event = JSON.parse(line);
    if (event.error) throw new Error(event.error);
    if (event.result) result = event.result;
    if (event.stage) update(event);
  }
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) accept(line);
    }
    accept(buffer + decoder.decode());
  } finally {
    reader.releaseLock();
  }
  if (!result) throw new Error("Kết nối đã dừng trước khi nhận kết quả.");
  return result;
}

const SESSION_KEY = "tkc-session";

export function currentSession(): Session | null {
  try {
    const stored = sessionStorage.getItem(SESSION_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

export function saveSession(session: Session | null) {
  if (session) sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  else sessionStorage.removeItem(SESSION_KEY);
}

export const riskLabels: Record<Risk, string> = {
  high: "Nguy cơ cao", medium: "Đáng ngờ", uncertain: "Cần xác minh", low: "Ít dấu hiệu",
};

export const entityLabels: Record<string, string> = {
  ACCOUNT: "Tài khoản", PHONE: "Số điện thoại", URL: "Tên miền",
};
