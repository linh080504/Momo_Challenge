"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Download, ShieldCheck } from "lucide-react";
import { api, type BrandCase, type BrandSource, type CampaignState } from "@/lib/api";
import { brandLabels } from "../analysis/brand-notice";

const queues: Record<CampaignState, string> = { pending: "Chờ duyệt", approved: "Đã duyệt", rejected: "Đã bác bỏ" };
const sources: Record<BrandSource, string> = {
  CT_LOGS: "Nhật ký chứng chỉ",
  CSKH_REPORT: "Báo cáo CSKH",
  QR_GATEWAY: "QR liên kết",
  THREAT_INTEL: "Nguồn tình báo",
  QUICK_CHECK: "Kiểm tra thủ công",
};
const DEMO_HOST = "momo-hoan-tien.example";
const DEMO_SNAPSHOT = '<h1>MoMo xác minh hoàn tiền</h1><p>Nhập mã OTP.</p><form><input autocomplete="one-time-code"></form>';
const ROOT = "/v1/ops/brand-cases";

type Queue = { items: BrandCase[]; next_cursor: string | null };
type Decision = "approve" | "reject" | "revoke";
const formatDate = (epoch: number) => new Date(epoch * 1000).toLocaleString("vi-VN");

export function BrandCases({ token }: { token: string }) {
  const [source, setSource] = useState<BrandSource>("CT_LOGS");
  const [addresses, setAddresses] = useState("");
  const [state, setState] = useState<CampaignState>("pending");
  const [queue, setQueue] = useState<Queue>();
  const [reload, setReload] = useState(0);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    api<Queue>(ROOT + "?state=" + state, "GET", undefined, token, controller.signal).then(setQueue)
      .catch(failure => { if (!controller.signal.aborted) setError((failure as Error).message); });
    return () => controller.abort();
  }, [token, state, reload]);

  async function intake(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const lines = addresses.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    if (!lines.length || busy) return;
    setBusy(true);
    setNotice("");
    setError("");
    try {
      const result = await api<{ created: number; updated: number; matched: number }>(
        ROOT + "/intake", "POST", { source, addresses: lines }, token,
      );
      setNotice(`Đã nhận ${result.matched} tên miền. ${result.created} hồ sơ mới, ${result.updated} hồ sơ bổ sung nguồn.`);
      setAddresses("");
      setState("pending");
      setReload(value => value + 1);
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function nextPage() {
    if (!queue?.next_cursor || busy) return;
    setBusy(true);
    setError("");
    try {
      const next = await api<Queue>(ROOT + "?state=" + state + "&after=" + encodeURIComponent(queue.next_cursor), "GET", undefined, token);
      setQueue({ items: [...queue.items, ...next.items], next_cursor: next.next_cursor });
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return <section className="panel page-panel brand-queue" aria-labelledby="brand-queue-title">
    <div className="panel-heading">
      <span className="heading-icon"><ShieldCheck size={22} aria-hidden="true" /></span>
      <div><h2 id="brand-queue-title">Website mạo danh MoMo</h2><p className="micro muted">Nhập tên miền, đối chiếu bằng chứng và duyệt cảnh báo.</p></div>
    </div>
    <details className="details">
      <summary>Nhập ứng viên</summary>
      <form className="stack" onSubmit={intake}>
        <label>Nguồn ứng viên <select value={source} disabled={busy} onChange={event => setSource(event.target.value as BrandSource)}>
          {Object.entries(sources).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </select></label>
        <label>Tên miền hoặc URL, mỗi dòng một mục
          <textarea rows={3} value={addresses} maxLength={60000} disabled={busy} onChange={event => setAddresses(event.target.value)} />
        </label>
        <div className="actions">
          <button className="button primary" disabled={busy || !addresses.trim()}>Thêm vào hàng duyệt</button>
          <button type="button" className="button secondary" disabled={busy} onClick={() => { setSource("CT_LOGS"); setAddresses(DEMO_HOST); }}>Dùng tên miền mẫu</button>
        </div>
      </form>
    </details>
    <label>Trạng thái hồ sơ
      <select value={state} disabled={busy} onChange={event => {
        setQueue(undefined);
        setError("");
        setState(event.target.value as CampaignState);
      }}>
        {Object.entries(queues).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
      </select>
    </label>
    {notice && <p role="status" className="notice">{notice}</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {queue?.items.length === 0 && <p className="muted">Chưa có hồ sơ trong trạng thái này.</p>}
    {queue?.items.map(item => <CaseCard key={item.host + item.revision} item={item} token={token} onUpdate={() => setReload(value => value + 1)} />)}
    {queue?.next_cursor && <div><button type="button" className="button secondary" onClick={nextPage} disabled={busy}>Xem thêm hồ sơ</button></div>}
  </section>;
}

function CaseCard({ item, token, onUpdate }: { item: BrandCase; token: string; onUpdate: () => void }) {
  const [html, setHtml] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const path = ROOT + "/" + encodeURIComponent(item.host);
  const editable = item.state !== "approved";

  async function submit(action: "evidence" | "decision", body: object) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await api(path + "/" + action, "POST", { ...body, revision: item.revision }, token);
      if (action === "evidence") setHtml("");
      onUpdate();
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function download() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const dossier = await api<object>(path + "/dossier", "GET", undefined, token);
      const url = URL.createObjectURL(new Blob([JSON.stringify(dossier, null, 2)], { type: "application/json" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = item.host + ".json";
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const decisionButton = (decision: Decision, label: string, style = "secondary") =>
    <button type="button" className={"button " + style} disabled={busy} onClick={() => void submit("decision", { decision })}>{label}</button>;

  return <article className="panel page-panel">
    <div>
      <h3 className="qr-host">{item.host}</h3>
      <p className="micro muted">{brandLabels[item.assessment.verdict]} · {item.assessment.version}</p>
      {item.expires && <p className="micro muted">Hết hạn cảnh báo {formatDate(item.expires)}</p>}
    </div>
    <ul className="question-list">
      {Object.entries(item.sources).map(([id, time]) => <li key={id}>{sources[id as BrandSource]} · {formatDate(time)}</li>)}
      {item.assessment.findings.map(finding => <li key={finding}>{finding}</li>)}
    </ul>
    {editable && <details className="details">
      <summary>Đối chiếu HTML đã thu thập</summary>
      <form className="stack" onSubmit={event => { event.preventDefault(); if (html.trim()) void submit("evidence", { html }); }}>
        <label>HTML đã kiểm tra nguồn
          <textarea value={html} rows={4} maxLength={35000} onChange={event => setHtml(event.target.value)} disabled={busy} />
        </label>
        <div className="actions">
          <button className="button primary" disabled={busy || !html.trim()}>Đối chiếu bằng chứng</button>
          {item.host === DEMO_HOST && <button type="button" className="button secondary" disabled={busy}
            onClick={() => setHtml(DEMO_SNAPSHOT)}>Dùng dữ liệu giả lập</button>}
        </div>
      </form>
    </details>}
    <div className="actions">
      {item.state === "pending" && item.assessment.verdict === "IMPOSTOR" && decisionButton("approve", "Duyệt cảnh báo MoMo", "primary")}
      {item.state === "pending" && decisionButton("reject", "Bác bỏ hồ sơ")}
      {item.state === "approved" && decisionButton("revoke", "Rút cảnh báo")}
      <button type="button" className="button secondary" onClick={download} disabled={busy}><Download size={18} aria-hidden="true" /> Xuất hồ sơ</button>
    </div>
    {error && <p role="alert" className="error">{error}</p>}
  </article>;
}
