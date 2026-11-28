"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { QRCodeSVG } from "qrcode.react";
import { ScanLine, ShieldCheck } from "lucide-react";
import { Upload } from "@/components/analysis/upload";
import { api, riskLabels, type BrandAlert, type Input, type Risk, type UrlCheck } from "@/lib/api";
import { type QrDraft } from "@/lib/check-draft";
import { imageInput } from "@/lib/images";
import { BrandNotice } from "./brand-notice";

type QrDetails = {
  kind: "payment";
  bank: string | null;
  bank_bin: string;
  account: string;
  amount: string | null;
  valid_crc: boolean;
  mismatch: boolean;
  confirmed_alert: boolean;
  risk: Risk;
  disclaimer: string;
} | (UrlCheck & { kind: "url"; confirmed_alert: boolean; threat_intel_match: boolean; risk: Risk; disclaimer: string; brand_alert?: BrandAlert | null });
type QrInput = Input & { payload?: string };

export function QrChecker({ embedded = false, headingLevel = "h1", initialDraft, onCheck }: {
  embedded?: boolean;
  headingLevel?: "h1" | "h2";
  initialDraft?: QrDraft;
  onCheck?: (draft: QrDraft) => void;
}) {
  const [file, setFile] = useState<File | null>(initialDraft?.file ?? null);
  const [payload, setPayload] = useState(initialDraft?.payload ?? "");
  const [text, setText] = useState(initialDraft?.text ?? "");
  const [result, setResult] = useState<QrDetails | null>(null);
  const [lastInput, setLastInput] = useState<QrInput | null>(null);
  const [clean, setClean] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const formElement = useRef<HTMLFormElement>(null);
  const resultElement = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!initialDraft) return;
    const timer = window.setTimeout(() => formElement.current?.requestSubmit(), 0);
    return () => window.clearTimeout(timer);
  }, [initialDraft]);

  useEffect(() => {
    if (initialDraft && result) resultElement.current?.scrollIntoView({ block: "start" });
  }, [initialDraft, result]);

  function clearResult() {
    setResult(null);
    setLastInput(null);
    setClean("");
    setConfirmed(false);
    setError("");
  }

  async function inspect(event: FormEvent) {
    event.preventDefault();
    if (busy || !(file || payload.trim())) return;
    if (onCheck) {
      onCheck({ kind: "qr", text, payload, file });
      return;
    }
    clearResult();
    setBusy(true);
    try {
      const input = { text, ...(file ? await imageInput(file) : { payload: payload.trim() }) };
      setResult(await api<QrDetails>("/v1/qr/parse", "POST", input));
      setLastInput(input);
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function regenerate() {
    if (!lastInput || !confirmed) return;
    setBusy(true);
    setError("");
    try {
      setClean((await api<{ payload: string }>("/v1/qr/build", "POST", { ...lastInput, confirmed: true })).payload);
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const InputPanel = embedded ? "div" : "section";
  const Heading = headingLevel;

  return <>
    <InputPanel className={embedded ? undefined : "panel page-panel"}>
      {!embedded && <>
        <span className="heading-icon"><ScanLine size={23} /></span>
        <Heading>Kiểm tra mã QR</Heading>
        <p className="muted">Đọc thông tin người nhận trong VietQR hoặc kiểm tra tên miền trong QR liên kết.</p>
      </>}
      <form ref={formElement} className="stack" onSubmit={inspect}>
        <Upload file={file} onChange={value => { clearResult(); setFile(value); if (value) setPayload(""); }} disabled={busy} mode="qr" />
        {!file && <label>Hoặc dán nội dung QR
          <input value={payload} maxLength={1024} disabled={busy} onChange={event => { clearResult(); setPayload(event.target.value); }} />
        </label>}
        <label>Tin nhắn đi kèm (tùy chọn)
          <textarea rows={3} value={text} maxLength={12000} disabled={busy} onChange={event => { clearResult(); setText(event.target.value); }}
            placeholder="Dán tin nhắn có thông tin người nhận để đối chiếu…" />
        </label>
        <button className={embedded ? "button primary check-button" : "button primary"} disabled={busy || !(file || payload.trim())}><ScanLine size={20} />{busy ? "Đang xử lý…" : "Kiểm tra mã"}</button>
      </form>
      {error && <p role="alert" className="error">{error}</p>}
    </InputPanel>
    {result?.kind === "url" && <section ref={resultElement} className="panel page-panel website-result-anchor">
      <div className="chips"><span className={"badge risk-" + result.risk}>{riskLabels[result.risk]}</span></div>
      <h2>QR liên kết</h2>
      <p>Tên miền đích <strong className="qr-host">{result.host}</strong></p>
      {result.brand_alert && <BrandNotice alert={result.brand_alert} />}
      {result.signals.length > 0 && <ul className="question-list">{result.signals.filter(item => item !== result.brand_alert?.finding).map(item => <li key={item}>{item}</li>)}</ul>}
      {result.threat_intel_match && <p className="notice">Google Safe Browsing ghi nhận tín hiệu nguy hiểm ở tên miền.</p>}
      {result.confirmed_alert && !result.brand_alert && <p className="notice verified"><ShieldCheck size={20} /> Cảnh báo đã được chuyên viên xác nhận.</p>}
      <p className="disclaimer">{result.disclaimer}</p>
    </section>}
    {result?.kind === "payment" && <section ref={resultElement} className="panel page-panel website-result-anchor">
      <div className="chips"><span className={"badge risk-" + result.risk}>{riskLabels[result.risk]}</span></div>
      <h2>Thông tin người nhận</h2>
      <dl className="qr-data">
        <div><dt>Ngân hàng</dt><dd>{result.bank || result.bank_bin}</dd></div>
        <div><dt>Số tài khoản</dt><dd>{result.account}</dd></div>
        <div><dt>Số tiền</dt><dd>{result.amount ? Number(result.amount).toLocaleString("vi-VN") + " đ" : "Chưa đặt"}</dd></div>
      </dl>
      {!result.valid_crc && <p className="error">Mã kiểm tra CRC không khớp.</p>}
      {result.mismatch && <p className="error">Tài khoản trong mã khác tài khoản trong tin nhắn.</p>}
      {result.confirmed_alert && <p className="notice verified"><ShieldCheck size={20} /> Cảnh báo đã được chuyên viên xác nhận.</p>}
      <p className="disclaimer">{result.disclaimer}</p>
      {result.risk === "low" && <div className="stack review">
        <label className="check-label">
          <input type="checkbox" checked={confirmed} onChange={event => { setConfirmed(event.target.checked); setClean(""); }} />
          Tôi đã kiểm tra đúng ngân hàng và người nhận
        </label>
        <button type="button" className="button primary" disabled={!confirmed || busy} onClick={regenerate}>Tạo lại VietQR</button>
        {clean && <div className="qr-code"><QRCodeSVG value={clean} size={210} marginSize={4} title="VietQR đã tạo lại" /></div>}
      </div>}
    </section>}
  </>;
}
