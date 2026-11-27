"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRef, useState } from "react";
import { Globe2, LayoutGrid, Menu, ScanLine, Search, UserRound, X } from "lucide-react";
import { BrandMascot, projectName } from "@/components/brand";

const links = [
  { href: "/", label: "Kiểm tra", icon: Search },
  { href: "/website", label: "Website", icon: Globe2 },
  { href: "/qr", label: "VietQR", icon: ScanLine },
  { href: "/ops", label: "Vận hành", icon: LayoutGrid },
  { href: "/login", label: "Tài khoản", icon: UserRound },
];

const landingLinks = [
  { href: "#dau-hieu", label: "Dấu hiệu" },
  { href: "#quy-trinh", label: "Quy trình" },
  { href: "#tinh-nang", label: "Tính năng" },
  { href: "#hoi-dap", label: "Hỏi đáp" },
];

function Brand() {
  return <Link href="/" className="brand">
    <span className="brand-mark"><BrandMascot size={33} /></span>
    {projectName}
  </Link>;
}

function LandingNavigation() {
  const [open, setOpen] = useState(false);
  const toggle = useRef<HTMLButtonElement>(null);

  return (
    <nav className="shell navigation landing-navigation" aria-label="Điều hướng chính"
      onKeyDown={event => {
        if (event.key === "Escape" && open) {
          setOpen(false);
          toggle.current?.focus();
        }
      }}>
      <Brand />
      <button type="button" className="landing-menu-toggle" ref={toggle}
        onClick={() => setOpen(value => !value)}
        aria-label={open ? "Đóng menu" : "Mở menu"} aria-expanded={open} aria-controls="landing-menu">
        {open ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
      </button>
      <div className="landing-menu" id="landing-menu" data-open={open}>
        {landingLinks.map(link => <a key={link.href} href={link.href} onClick={() => setOpen(false)}>{link.label}</a>)}
        {links.slice(1).map(link => <Link key={link.href} href={link.href} className={link.href === "/website" ? undefined : "landing-menu-utility"}
          onClick={() => setOpen(false)}>{link.label}</Link>)}
      </div>
      <a className="button primary landing-nav-cta" href="#kiem-tra">Kiểm tra ngay</a>
    </nav>
  );
}

export function SiteNavigation() {
  const pathname = usePathname();
  if (pathname === "/") return <LandingNavigation />;

  return (
    <nav className="shell navigation" aria-label="Điều hướng chính">
      <Brand />
      <div className="nav-links">
        {links.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/");
          return <Link key={href} href={href} aria-current={active ? "page" : undefined}
            className={href === "/login" ? "nav-account" : undefined}>
            <Icon size={17} aria-hidden="true" /><span>{label}</span>
          </Link>;
        })}
      </div>
    </nav>
  );
}
