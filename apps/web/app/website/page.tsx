import type { Metadata } from "next";
import { Globe2 } from "lucide-react";
import { AnalyzerForm } from "@/components/analysis/analyzer-form";

export const metadata: Metadata = {
  title: "Kiểm tra website",
  description: "Đối chiếu tên miền và đọc ảnh chụp để nhận diện dấu hiệu website giả mạo.",
};

export default function WebsitePage() {
  return <div className="shell website-page">
    <div className="website-intro">
      <span className="heading-icon"><Globe2 size={26} aria-hidden="true" /></span>
      <h1>Kiểm tra website nghi lừa đảo</h1>
      <p>Dán link để tự phân tích nội dung công khai, chụp ảnh trang và đối chiếu nguồn.</p>
    </div>
    <AnalyzerForm website />
  </div>;
}
