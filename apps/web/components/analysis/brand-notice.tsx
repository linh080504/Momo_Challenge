import { ShieldAlert } from "lucide-react";
import type { BrandAlert, BrandVerdict } from "@/lib/api";

export const brandLabels: Record<BrandVerdict, string> = {
  BENIGN: "Chưa thấy dấu hiệu mạo danh",
  ABSTAIN_NEEDS_REVIEW: "Cần xác minh",
  IMPOSTOR: "Có dấu hiệu mạo danh MoMo",
};

export function BrandNotice({ alert }: { alert: BrandAlert }) {
  return <div className="notice error">
    <ShieldAlert size={21} aria-hidden="true" />
    <div>
      <strong>{alert.finding}</strong>
      <p className="qr-host">{alert.host}</p>
      <a href="https://www.momo.vn/hoi-dap" target="_blank" rel="noopener noreferrer">Mở Trợ giúp MoMo để xác minh</a>
    </div>
  </div>;
}
