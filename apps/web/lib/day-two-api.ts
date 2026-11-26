// Client gọi POST /v1/analyze (JSON base64, KHÔNG multipart — docs/DECISIONS.md 2026-11-24).
//
// ── Tiến trình thật ────────────────────────────────────────────────────────────────
// Màn chờ chỉ hiện những gì máy chủ THỰC SỰ báo. Hợp đồng hiện tại của /v1/analyze chỉ trả một
// JSON ở cuối nên chưa có sự kiện nào; khi đó giao diện hiện danh sách 3 việc kèm "đang chờ",
// KHÔNG giả vờ từng bước đã xong bằng đồng hồ.
//
// ĐỀ XUẤT (chưa được BE/PM chấp nhận, cần ghi docs/DECISIONS.md trước khi BE làm):
// nếu client gửi `Accept: application/x-ndjson` và máy chủ hỗ trợ, trả về NDJSON — mỗi dòng một
// đối tượng JSON:
//   {"done":"read"}                                        đã đọc xong ảnh / tin nhắn
//   {"done":"entities","entities":[{"type","display"}]}    đã trích thực thể (chỉ `display` đã che)
//   {"done":"evidence"}                                    đã tra xong bằng chứng
//   {"result":{...}}                                       kết quả cuối, đúng analysis.schema.json
//   {"error":"..."}                                        lỗi giữa chừng
// Máy chủ không hỗ trợ thì cứ trả application/json như cũ: client tự lùi về chế độ chờ.
// Sự kiện tiến trình KHÔNG được mang mức nguy cơ (brief 5.1: không hiện kết luận sơ bộ rồi đổi).

import { parseAnalysis, type Analysis, type EntityType } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

/** Máy chủ trả chậm hơn mức này thì coi là lỗi (p95 ảnh chính thức là ≤ 12s). */
const DEFAULT_TIMEOUT_MS = 45_000;

export type StageId = "read" | "entities" | "evidence";

export interface EntityPreview {
  type?: EntityType;
  display: string;
}

export type ProgressEvent =
  | { done: "read" }
  | { done: "entities"; entities: EntityPreview[] }
  | { done: "evidence" };

export interface AnalyzeInput {
  /** "" nếu chỉ có ảnh. */
  text: string;
  image?: { base64: string; mime: "image/jpeg" | "image/png" };
}

export type AnalyzeErrorKind = "network" | "timeout" | "http" | "invalid" | "aborted";

/** `message` luôn là tiếng Việt, đưa thẳng cho người dùng đọc. */
export class AnalyzeError extends Error {
  constructor(
    readonly kind: AnalyzeErrorKind,
    message: string,
    readonly status?: number,
  ) {
    super(message);
  }
}

const STATUS_FALLBACK: Record<number, string> = {
  413: "Ảnh quá lớn. Hãy chọn ảnh khác hoặc cắt bớt phần thừa.",
  415: "Chỉ nhận ảnh PNG hoặc JPEG.",
  422: "Cần có tin nhắn hoặc ảnh để kiểm tra.",
};

async function errorFromResponse(res: Response): Promise<AnalyzeError> {
  // Hợp đồng: 413/415/422 kèm thông báo tiếng Việt. 5xx thì dùng câu của giao diện,
  // vì nội dung lỗi nội bộ có thể là tiếng Anh hoặc mã kỹ thuật.
  if (STATUS_FALLBACK[res.status]) {
    let serverMessage: string | null = null;
    try {
      const body: unknown = await res.json();
      if (typeof body === "object" && body !== null) {
        const b = body as Record<string, unknown>;
        const candidate = b.error ?? b.detail ?? b.message;
        if (typeof candidate === "string" && candidate.trim()) serverMessage = candidate.trim();
      }
    } catch {
      /* thân phản hồi không phải JSON: dùng câu mặc định */
    }
    return new AnalyzeError("http", serverMessage ?? STATUS_FALLBACK[res.status], res.status);
  }
  return new AnalyzeError(
    "http",
    res.status >= 500
      ? "Hệ thống phân tích đang gặp sự cố. Hãy thử lại sau ít phút."
      : "Yêu cầu không thành công. Hãy thử lại.",
    res.status,
  );
}

const INVALID_RESULT = () =>
  new AnalyzeError("invalid", "Máy chủ trả về kết quả mà trang này không đọc được.");

function toEntityPreviews(value: unknown): EntityPreview[] {
  if (!Array.isArray(value)) return [];
  const out: EntityPreview[] = [];
  for (const item of value) {
    if (typeof item === "object" && item !== null) {
      const e = item as Record<string, unknown>;
      // Chỉ lấy `display` (đã che). Không bao giờ hiện `token` hay giá trị thô.
      if (typeof e.display === "string" && e.display) {
        out.push({ type: e.type as EntityType | undefined, display: e.display });
      }
    }
  }
  return out;
}

function toProgressEvent(raw: Record<string, unknown>): ProgressEvent | null {
  switch (raw.stage ?? raw.done) {
    case "image_read":
    case "read":
      return { done: "read" };
    case "entities":
      return { done: "entities", entities: toEntityPreviews(raw.entities) };
    case "evidence":
      return { done: "evidence" };
    default:
      return null;
  }
}

async function readNdjson(
  res: Response,
  onProgress: ((e: ProgressEvent) => void) | undefined,
): Promise<Analysis> {
  if (!res.body) throw INVALID_RESULT();
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  // Dùng object thay vì `let`: TypeScript không theo dõi phép gán bên trong closure.
  const final: { value: Analysis | null } = { value: null };

  const handleLine = (line: string) => {
    if (!line.trim()) return;
    let raw: unknown;
    try {
      raw = JSON.parse(line);
    } catch {
      throw INVALID_RESULT();
    }
    if (typeof raw !== "object" || raw === null) throw INVALID_RESULT();
    const obj = raw as Record<string, unknown>;

    if ("result" in obj) {
      const parsed = parseAnalysis(obj.result);
      if (!parsed) throw INVALID_RESULT();
      final.value = parsed;
    } else if ("error" in obj) {
      const message = typeof obj.error === "string" ? obj.error : "Hệ thống phân tích đang gặp sự cố. Hãy thử lại sau ít phút.";
      throw new AnalyzeError("http", message, typeof obj.status === "number" ? obj.status : 502);
    } else {
      const event = toProgressEvent(obj);
      if (event) onProgress?.(event);
    }
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let newline: number;
    while ((newline = buffer.indexOf("\n")) >= 0) {
      handleLine(buffer.slice(0, newline));
      buffer = buffer.slice(newline + 1);
    }
  }
  handleLine(buffer + decoder.decode());

  if (!final.value) throw INVALID_RESULT();
  return final.value;
}

export interface AnalyzeOptions {
  /** Người dùng bấm "Dừng lại". */
  signal: AbortSignal;
  onProgress?: (event: ProgressEvent) => void;
  timeoutMs?: number;
}

export async function analyze(input: AnalyzeInput, options: AnalyzeOptions): Promise<Analysis> {
  const { signal, onProgress, timeoutMs = DEFAULT_TIMEOUT_MS } = options;

  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const forwardAbort = () => controller.abort();
  if (signal.aborted) controller.abort();
  signal.addEventListener("abort", forwardAbort);

  const body: Record<string, string> = { text: input.text };
  if (input.image) {
    body.image_base64 = input.image.base64;
    body.image_mime = input.image.mime;
  }

  try {
    const request: RequestInit = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/x-ndjson, application/json;q=0.9",
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    };
    let res = await fetch(`${API_URL}/v1/analyze/stream`, request);
    if (res.status === 404) res = await fetch(`${API_URL}/v1/analyze`, request);

    if (!res.ok) throw await errorFromResponse(res);

    if ((res.headers.get("content-type") ?? "").includes("application/x-ndjson")) {
      return await readNdjson(res, onProgress);
    }

    let json: unknown;
    try {
      json = await res.json();
    } catch {
      throw INVALID_RESULT();
    }
    const parsed = parseAnalysis(json);
    if (!parsed) throw INVALID_RESULT();
    return parsed;
  } catch (err) {
    if (err instanceof AnalyzeError) throw err;
    if (timedOut) {
      throw new AnalyzeError("timeout", "Máy chủ trả lời quá lâu nên đã dừng lại.");
    }
    if (signal.aborted) throw new AnalyzeError("aborted", "Đã dừng.");
    throw new AnalyzeError(
      "network",
      "Không kết nối được với máy chủ. Hãy kiểm tra mạng rồi thử lại.",
    );
  } finally {
    clearTimeout(timer);
    signal.removeEventListener("abort", forwardAbort);
  }
}
