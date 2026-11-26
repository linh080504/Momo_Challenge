"use client";

import { useState } from "react";
import { AlertTriangle, Check, CircleHelp, Flag, Info, LockKeyhole, Share2, ShieldCheck } from "lucide-react";
import { api, ApiError, entityLabels, riskLabels, saveSession, type Analysis, type Session } from "@/lib/api";
import { projectName } from "@/components/brand";
import { LoginForm } from "@/components/login-form";
import { ReceiptEvidence } from "./receipt-evidence";

const sources: Record<string, string> = {
  internal_blacklist: "Chiến dịch đã duyệt",
  domain_check: "Kiểm tra tên miền",
  safe_browsing: "Google Safe Browsing",
  rules: "Dấu hiệu theo quy tắc",
  llm: "Mô hình phân tích",
  vietqr: "Kiểm tra VietQR",
  document: "Phân tích biên lai",
  rdap: "Dữ liệu đăng ký tên miền",
  fraud_url_ml: "Mô hình nhận diện phishing",
};

export function Result({ result, initialSession, receipt }: { result: Analysis; initialSession: Session | null; receipt?: File | null }) {
  const [session, setSession] = useState(initialSession);
  const [signingIn, setSigningIn] = useState(false);
  const [reported, setReported] = useState(false);
  const [pending, setPending] = useState<"report" | "share" | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [shareUrl, setShareUrl] = useState("");
  const confirmed = result.evidence.some(item => item.source === "internal_blacklist" && item.weight > 0);

  async function report(activeSession: Session) {
    setPending("report");
    setError("");
    try {
      await api("/v1/reports", "POST", { analysis_id: result.analysis_id, consent: true }, activeSession.token);
      setReported(true);
      setSigningIn(false);
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) {
        saveSession(null);
        setSession(null);
        setSigningIn(true);
      }
      setError((failure as Error).message);
    } finally {
      setPending(null);
    }
  }

  async function share() {
    setPending("share");
    setError("");
    setMessage("");
    try {
      const { token } = await api<{ token: string }>("/v1/shares", "POST", { analysis_id: result.analysis_id }, session?.token);
      const url = new URL("/share/" + encodeURIComponent(token), window.location.origin).toString();
      setShareUrl(url);
      if (navigator.share) {
        try { await navigator.share({ title: projectName, url }); }
        catch (failure) { if ((failure as Error).name !== "AbortError") setMessage("Bạn có thể sao chép liên kết bên dưới."); }
      } else if (navigator.clipboard) {
        await navigator.clipboard.writeText(url).catch(() => undefined);
        setMessage("Liên kết sẵn sàng để chia sẻ.");
      }
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setPending(null);
    }
  }

  return (
    <section className="panel result-panel" aria-label="Kết quả phân tích">
      <div className={"result-banner risk-" + result.risk_level}>
        <span className="result-icon">{result.risk_level === "low" ? <ShieldCheck size={26} /> : <AlertTriangle size={26} />}</span>
        <div><h2>{riskLabels[result.risk_level]}</h2><p>{result.summary}</p></div>
        <div className="result-score" aria-label={result.risk_score + " trên 100"}>{result.risk_score}<small>/100</small></div>
      </div>
      <div className="result-body">
        {confirmed && <p className="notice verified"><ShieldCheck size={20} /> Cảnh báo đã được chuyên viên xác nhận.</p>}
        {result.degraded && <p className="notice"><Info size={19} /> Chế độ hạn chế. Một phần dịch vụ đối chiếu hoặc mô hình đang tắt hoặc gián đoạn.</p>}
        {result.document && <ReceiptEvidence evidence={result.document} file={receipt} />}
        {result.url_checks && <details className="details">
          <summary>Kiểm tra tên miền</summary>
          <ul className="evidence">{result.url_checks.map((item, index) => <li key={item.host + index}>
            <strong className="qr-host">{item.host}</strong>
            {item.domain_age_days !== null && <p>Đã đăng ký {item.domain_age_days} ngày trước</p>}
            {item.signals.map(signal => <p key={signal}>{signal}</p>)}
          </li>)}</ul>
        </details>}
        <h3>Dấu hiệu nhận thấy</h3>
        {result.red_flags.length ? <ul className="flag-list">{result.red_flags.map(flag =>
          <li key={flag.quote + flag.reason}><blockquote>“{flag.quote}”</blockquote><p>{flag.reason}</p></li>
        )}</ul> : <p className="muted">Chưa có đủ câu chữ để trích dẫn trực tiếp.</p>}
        <h3><CircleHelp size={19} /> Câu hỏi kiểm chứng</h3>
        <ul className="question-list">{result.verification_questions.map(question => <li key={question}>{question}</li>)}</ul>
        {!!result.guidance?.length && <details className="details">
          <summary>Hướng dẫn theo nhóm thủ đoạn</summary>
          <ul className="question-list">{result.guidance.map(item => <li key={item.id}>{item.text}</li>)}</ul>
        </details>}
        {(result.entities.length > 0 || result.evidence.length > 0) &&
          <details className="details">
            <summary>Xem bằng chứng và thông tin đã trích</summary>
            {result.entities.length > 0 && <div className="chips">{result.entities.map((entity, index) =>
              <span className="chip" key={index}>{entityLabels[entity.type] || entity.type} · {entity.display}</span>
            )}</div>}
            <ul className="evidence">{result.evidence.map((item, index) => <li key={item.source + index}>
              <strong>{sources[item.source] || item.source}</strong><p>{item.finding}</p>
            </li>)}</ul>
          </details>}
        <p className="disclaimer">{result.ai_disclaimer}</p>
        <div className="actions">
          <button type="button" className="button primary" disabled={reported || pending !== null}
            onClick={() => session ? void report(session) : setSigningIn(true)}>
            {reported ? <Check size={19} /> : <Flag size={19} />}
            {reported ? "Đã báo cáo" : pending === "report" ? "Đang gửi…" : "Báo cáo"}
          </button>
          <button type="button" className="button secondary" disabled={pending !== null} onClick={share}><Share2 size={18} />
            {pending === "share" ? "Đang tạo liên kết…" : "Hỏi người thân"}
          </button>
        </div>
        <p className="micro muted"><LockKeyhole size={15} /> Khi báo cáo, bạn đồng ý gửi tín hiệu và mã đối chiếu đã che cho đội vận hành.</p>
        {signingIn && <div className="inline-login">
          <h3>Đăng nhập để gửi báo cáo</h3>
          <LoginForm button="Đăng nhập và báo cáo" onSignedIn={active => {
            setSession(active);
            void report(active);
          }} />
        </div>}
        {error && <p role="alert" className="error">{error}</p>}
        {message && <p role="status" className="muted">{message}</p>}
        {shareUrl && <label>Liên kết đã che thông tin, có hiệu lực 24 giờ
          <input readOnly value={shareUrl} onFocus={event => event.target.select()} />
        </label>}
      </div>
    </section>
  );
}
