import type { Metadata } from "next";
import Link from "next/link";
import { BrandMascot, projectName } from "@/components/brand";
import { SiteNavigation } from "@/components/site-navigation";
import "./styles.css";

export const metadata: Metadata = {
  title: { default: projectName, template: "%s · " + projectName },
  description: "Kiểm tra tin nhắn, ảnh chụp và VietQR đáng ngờ trước khi chuyển tiền.",
};

export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>
        <header className="site-header">
          <SiteNavigation />
        </header>
        <main className="main-content">{children}</main>
        <footer className="site-footer"><div className="shell footer-inner">
          <span className="footer-brand"><BrandMascot size={22} />{projectName}</span>
          <div className="footer-links"><Link href="/qr">VietQR</Link><Link href="/ops">Vận hành</Link><Link href="/login">Tài khoản</Link></div>
          <span>Hãy xác minh qua kênh chính thức trước khi chuyển tiền.</span>
        </div></footer>
      </body>
    </html>
  );
}
