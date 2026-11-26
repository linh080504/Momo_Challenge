export const apiBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export type Risk = "high" | "medium" | "uncertain" | "low";
export type Entity = { type: string; display: string };
export type Analysis = {
  analysis_id: string;
  risk_level: Risk;
  risk_score: number;
  scenario_group: string | null;
  summary: string;
  red_flags: { quote: string; reason: string }[];
  verification_questions: string[];
  evidence: { source: string; finding: string; weight: number }[];
  entities: Entity[];
  ai_disclaimer: string;
  degraded: boolean;
};
export type AnalysisEvent = {
  stage: string;
  message: string;
  entities?: Entity[];
};
export type Input = { text: string; image_base64?: string; image_mime?: string };
export type Account = { email: string; role: "user" | "ops" };
export type Session = Account & { token: string };
export type CampaignState = "pending" | "approved" | "rejected";
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
  history: { actor: string; action: "approve" | "reject" | "edit_group"; created: number }[];
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
