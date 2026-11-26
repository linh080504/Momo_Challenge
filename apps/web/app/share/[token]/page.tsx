import Link from "next/link";
import { LockKeyhole } from "lucide-react";
import { apiBase, riskLabels, type Risk } from "@/lib/api";

type Shared = { risk: Risk; summary: string; disclaimer: string };

export default async function SharedPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const base = (process.env.API_INTERNAL_URL || apiBase).replace(/\/+$/, "");
  const result: Shared | null = await fetch(base + "/v1/shares/" + encodeURIComponent(token), {
    cache: "no-store",
  }).then(response => response.ok ? response.json() : null).catch(() => null);
  return <div className="narrow page-section"><section className="panel page-panel">
    <span className="heading-icon"><LockKeyhole size={23} /></span>
    <h1>Kết quả được chia sẻ</h1>
    {result ? <div className="stack">
      <div><span className={"badge risk-" + result.risk}>{riskLabels[result.risk]}</span></div>
      <p>{result.summary}</p><p className="disclaimer">{result.disclaimer}</p>
    </div> : <p className="muted">Liên kết đã hết hạn hoặc tạm thời không mở được.</p>}
    <Link href="/" className="button primary">Kiểm tra nội dung của bạn</Link>
  </section></div>;
}
