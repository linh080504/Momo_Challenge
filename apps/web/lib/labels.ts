// Nhãn tiếng Việt cho các giá trị enum trong schema.
// Đây là phép ĐỔI TÊN để hiển thị, không phải phán đoán: mức nguy cơ luôn do máy chủ quyết định.

import type {
  EntityType,
  EvidenceSource,
  RecommendedAction,
  RiskLevel,
  ScenarioGroup,
  Tactic,
} from "./types";

export interface RiskStyle {
  /** Chữ lớn trên băng rôn. Màu luôn đi kèm chữ, không dùng màu một mình. */
  label: string;
  /** Một câu giải thích ngắn dưới nhãn. */
  hint: string;
  banner: string;
  badge: string;
}

export const RISK: Record<RiskLevel, RiskStyle> = {
  high: {
    label: "NGUY CƠ CAO",
    hint: "Rất đáng ngờ. Đừng chuyển tiền.",
    banner: "bg-red-700 text-white border-red-900",
    badge: "bg-red-100 text-red-900",
  },
  medium: {
    label: "NGUY CƠ TRUNG BÌNH",
    hint: "Có dấu hiệu đáng ngờ. Hãy kiểm tra kỹ trước khi làm tiếp.",
    banner: "bg-amber-300 text-amber-950 border-amber-600",
    badge: "bg-amber-100 text-amber-950",
  },
  low: {
    label: "NGUY CƠ THẤP",
    // Cố ý không dùng chữ "an toàn" (prompt v0 quy tắc 4): mức thấp không phải lời bảo đảm.
    hint: "Chưa thấy dấu hiệu lừa đảo rõ ràng. Vẫn nên tự xác minh trước khi chuyển tiền.",
    banner: "bg-sky-100 text-sky-950 border-sky-700",
    badge: "bg-sky-100 text-sky-950",
  },
  uncertain: {
    label: "CHƯA ĐỦ THÔNG TIN",
    hint: "AI chưa thể kết luận. Hãy xác minh bằng cách khác.",
    banner: "bg-slate-200 text-slate-900 border-slate-600",
    badge: "bg-slate-200 text-slate-900",
  },
};

export const ACTION_TEXT: Record<RecommendedAction, { title: string; body: string }> = {
  stop_and_verify: {
    title: "Dừng lại, chưa chuyển tiền",
    body: "Gọi số tổng đài chính thức (in trên thẻ hoặc trên website, app chính thức) để hỏi lại. Không gọi số có trong tin nhắn.",
  },
  ask_guardian: {
    title: "Hỏi người thân trước",
    body: "Hãy cho người thân hoặc người bạn tin tưởng xem tin nhắn này trước khi làm tiếp.",
  },
  report: {
    title: "Nên báo cáo tin này",
    body: "Báo cáo giúp cảnh báo những người khác nhận cùng một tin nhắn.",
  },
  proceed_with_clean_qr: {
    title: "Kiểm tra tên người nhận",
    body: "Trước khi chuyển, hãy đọc kỹ tên người nhận hiện trên app ngân hàng và chắc chắn đó đúng là người bạn định chuyển.",
  },
  no_action: {
    title: "Chưa cần làm gì thêm",
    body: "Vẫn nên cẩn thận với bất kỳ yêu cầu chuyển tiền nào bạn không chủ động.",
  },
};

export const GROUP_NAME: Record<ScenarioGroup, string> = {
  G1: "Mạo danh cơ quan, tổ chức",
  G2: "AI, deepfake, mạo danh người quen",
  G3: "Đầu tư tài chính, tuyển dụng",
  G4: "Mua bán, giao dịch trực tuyến",
  G5: "Đánh cắp dữ liệu, chiếm quyền thiết bị",
};

export const TACTIC: Record<Tactic, string> = {
  urgency: "Hối thúc",
  authority: "Mạo danh quyền lực",
  secrecy: "Bắt giữ bí mật",
  greed: "Mồi lợi nhuận",
  fear: "Đe dọa",
  personal_account: "Tài khoản cá nhân",
  credential_request: "Đòi OTP, mật khẩu",
  app_install: "Bắt cài ứng dụng",
  link: "Đường link lạ",
  other: "Dấu hiệu khác",
};

export const ENTITY_TYPE: Record<EntityType, string> = {
  ACCOUNT: "Số tài khoản",
  PHONE: "Số điện thoại",
  URL: "Đường link",
  EMAIL: "Email",
  CARD: "Số thẻ",
  AMOUNT: "Số tiền",
  BANK: "Ngân hàng",
  ORG: "Tổ chức",
};

export const EVIDENCE_SOURCE: Record<EvidenceSource, string> = {
  internal_blacklist: "Danh sách cảnh báo của hệ thống",
  safe_browsing: "Google Safe Browsing",
  domain_check: "Kiểm tra tên miền",
  rdap: "Tra cứu đăng ký tên miền",
  vietqr: "Đọc mã VietQR",
  rules: "Luật nhận diện",
  llm: "AI đọc hiểu nội dung",
};

/** Tra nhãn an toàn: giá trị lạ (schema đổi) thì hiện nguyên văn thay vì vỡ giao diện. */
export function labelOf<K extends string>(map: Record<K, string>, key: string | undefined): string | null {
  if (!key) return null;
  return (map as Record<string, string>)[key] ?? key;
}
