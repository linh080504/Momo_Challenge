import type { Metadata } from "next";
import { ShieldCheck } from "lucide-react";
import { TransferChecker } from "@/components/analysis/transfer-checker";

export const metadata: Metadata = {
  title: "Kiểm tra trước khi xác nhận",
  description: "Kiểm tra mã QR và lời nhắn để biết tiền sẽ chuyển đi đâu trước khi xác nhận trên MoMo.",
};

export default function TransferCheckPage() {
  return <div className="shell page-section transfer-page">
    <header className="website-intro">
      <span className="heading-icon"><ShieldCheck size={26} aria-hidden="true" /></span>
      <h1>Kiểm tra trước khi xác nhận</h1>
      <p>Kiểm tra mã QR và lời nhắn để biết tiền sẽ chuyển đi đâu trước khi xác nhận trên MoMo.</p>
    </header>
    <TransferChecker />
  </div>;
}
