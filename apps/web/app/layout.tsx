import type { Metadata, Viewport } from "next";
import { Be_Vietnam_Pro } from "next/font/google";
import "./globals.css";

const beVietnam = Be_Vietnam_Pro({
  variable: "--font-be-vietnam",
  subsets: ["vietnamese", "latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Trước Khi Chuyển — Kiểm tra tin nhắn trước khi chuyển tiền",
  description:
    "Dán tin nhắn hoặc tải ảnh chụp màn hình. AI chỉ ra dấu hiệu lừa đảo trước khi bạn chuyển tiền.",
};

// Không khóa zoom (maximumScale) để người lớn tuổi vẫn phóng to được.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#1d4ed8",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="vi" className={`${beVietnam.variable} h-full antialiased`}>
      <body className="min-h-full font-sans">{children}</body>
    </html>
  );
}
