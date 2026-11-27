import type { Metadata } from "next";
import { WebsiteWorkspace } from "@/components/analysis/website-workspace";

export const metadata: Metadata = {
  title: "Kiểm tra nội dung đáng ngờ",
  description: "Kiểm tra website, tin nhắn, ảnh chụp, mã QR, biên lai và ghi âm trước khi chuyển tiền.",
};

export default function WebsitePage() {
  return <WebsiteWorkspace />;
}
