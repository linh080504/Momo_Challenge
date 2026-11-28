"use client";

import { useEffect, useRef, useState, type FormEvent, type RefObject } from "react";
import { AlertTriangle, ArrowDownLeft, ArrowUpRight, LoaderCircle, ScanLine, ShieldCheck } from "lucide-react";
import { analyze, ApiError, currentSession, saveSession, type Analysis, type Session, type TransferIntent, type TransferReview } from "@/lib/api";
import { imageInput } from "@/lib/images";
import { ResultActions } from "./result-actions";
import { BrandNotice } from "./brand-notice";
import { Upload } from "./upload";

const HELP_URL = "https://www.momo.vn/hoi-dap";
const REPORT_URL = "https://www.momo.vn/an-toan-bao-mat/bao-cao-lua-dao";
// Test fixture for the parser. The sample QR is never displayed as a scannable image.
const SAMPLE_PAYLOAD = "00020101021238540010A00000072701240006970436011000000000000208QRIBFTTA530370454065000005802VN6304651C";
const SAMPLE_MESSAGE = "Bạn nhận hoàn tiền 500.000 ₫. Vui lòng quét mã QR để xác nhận.";
const intentLabels: Record<TransferIntent, string> = {
  receive: "Tôi đang chờ nhận tiền",
  pay: "Tôi đang trả tiền",
};
const unknownDetails = {
  unreadable: "Hãy thử ảnh rõ hơn, thấy đủ bốn góc mã QR.",
  invalid_crc: "Mã kiểm tra VietQR không khớp. Hãy lấy lại ảnh mã từ nguồn bạn đã xác minh.",
  link: "Mã chứa đường dẫn. Hãy xác minh yêu cầu qua kênh chính thức trước khi mở đường dẫn.",
  unsupported: "Đã đọc mã, nhưng chưa xác định được chiều tiền. Hiện hỗ trợ VietQR chuyển khoản VND.",
  unavailable: "Bộ đọc mã QR đang bận hoặc gián đoạn. Hãy thử lại sau.",
};

export function TransferChecker() {
  const [intent, setIntent] = useState<TransferIntent>();
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [sample, setSample] = useState(false);
  const [result, setResult] = useState<Analysis | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const active = useRef<AbortController | null>(null);
  const form = useRef<HTMLFormElement>(null);
  const resultHeading = useRef<HTMLHeadingElement>(null);

  useEffect(() => () => active.current?.abort(), []);
  useEffect(() => { if (result) resultHeading.current?.focus(); }, [result]);

  function clearResult() {
    setResult(null);
    setError("");
  }

  function loadSample() {
    clearResult();
    setIntent("receive");
    setFile(null);
    setSample(true);
    setText(SAMPLE_MESSAGE);
  }

  async function inspect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!intent || (!file && !sample) || active.current) return;
    clearResult();
    setProgress("Đang chuẩn bị kiểm tra…");
    const controller = new AbortController();
    active.current = controller;
    const timeout = window.setTimeout(() => controller.abort("timeout"), 45000);
    try {
      const input = {
        text: text.trim(),
        transfer_intent: intent,
        ...(file ? { ...await imageInput(file), qwen_vision: true } : { qr_payload: SAMPLE_PAYLOAD }),
      };
      const update = ({ message }: { message: string }) => setProgress(message);
      let signedIn = sample ? null : currentSession();
      let checked;
      try {
        checked = await analyze(input, update, signedIn?.token, controller.signal);
      } catch (failure) {
        if (!(failure instanceof ApiError && failure.status === 401 && signedIn)) throw failure;
        signedIn = null;
        saveSession(null);
        checked = await analyze(input, update, undefined, controller.signal);
      }
      if (!checked.transfer_review) throw new Error("Dịch vụ chưa hỗ trợ kiểm tra mục đích giao dịch.");
      setSession(signedIn);
      setResult(checked);
    } catch (failure) {
      if (controller.signal.reason === "timeout") setError("Kiểm tra mất nhiều thời gian. Hãy thử lại.");
      else if (!controller.signal.aborted) setError((failure as Error).message);
    } finally {
      window.clearTimeout(timeout);
      active.current = null;
      setProgress("");
    }
  }

  const busy = Boolean(progress);
  return <div className="stack">
    <form ref={form} tabIndex={-1} className="panel page-panel transfer-form" onSubmit={inspect}>
      <fieldset className="transfer-intents" disabled={busy}>
        <legend>Bạn đang muốn làm gì?</legend>
        {(["receive", "pay"] as const).map(value => <label key={value} className="transfer-intent" data-selected={intent === value}>
          <input type="radio" name="transfer-intent" value={value} checked={intent === value} onChange={() => { clearResult(); setIntent(value); }} />
          {value === "receive" ? <ArrowDownLeft size={20} aria-hidden="true" /> : <ArrowUpRight size={20} aria-hidden="true" />}
          {intentLabels[value]}
        </label>)}
      </fieldset>
      <Upload mode="qr" file={file} disabled={busy} onChange={value => {
        clearResult();
        setFile(value);
        if (sample) setText("");
        setSample(false);
      }} />
      <p className="micro muted">Bạn có thể chọn một ảnh chứa cả tin nhắn và mã QR. Ảnh được gửi đến QwenCloud để đọc chữ. Hãy che thông tin riêng tư quanh mã trước khi gửi.</p>
      <label>Tin nhắn đi kèm (tùy chọn)
        <textarea rows={3} maxLength={12000} value={text} disabled={busy} readOnly={sample} onChange={event => {
          clearResult();
          setText(event.target.value);
        }} placeholder="Dán lời nhắn bạn nhận được…" />
      </label>
      {sample && <p className="notice">Đang dùng dữ liệu giả lập. Số tiền trong mã mẫu là 500.000 ₫.</p>}
      <div className="actions">
        <button className="button primary" disabled={busy || !intent || !(file || sample)}>
          {busy ? <LoaderCircle size={19} className="spinning" aria-hidden="true" /> : <ScanLine size={19} aria-hidden="true" />}
          {busy ? "Đang kiểm tra…" : "Kiểm tra ngay"}
        </button>
        <button className="button secondary" type="button" disabled={busy} onClick={loadSample}>Thử tình huống hoàn tiền</button>
      </div>
      <div role="status" className={progress ? "muted" : "visually-hidden"}>{progress}</div>
      {error && <p role="alert" className="error">{error}</p>}
    </form>
    {result?.transfer_review && <TransferResult key={result.analysis_id} result={result} review={result.transfer_review} session={session} sample={sample}
      heading={resultHeading} reset={() => { clearResult(); form.current?.focus(); }} />}
    <details className="panel page-panel transfer-sent">
      <summary>Tôi đã chuyển tiền</summary>
      <p>Liên hệ Trợ giúp MoMo để được hướng dẫn xử lý giao dịch. Bạn có thể giữ lại biên nhận và nội dung trao đổi để cung cấp qua kênh chính thức khi cần.</p>
      <SupportLinks includeReport />
    </details>
  </div>;
}

function SupportLinks({ includeReport = false }: { includeReport?: boolean }) {
  return <div className="actions">
    <a className="button primary" href={HELP_URL} target="_blank" rel="noopener noreferrer">Mở Trợ giúp MoMo</a>
    {includeReport && <a className="button secondary" href={REPORT_URL} target="_blank" rel="noopener noreferrer">Kênh báo cáo của MoMo</a>}
  </div>;
}

function TransferResult({ result, review, session, sample, heading, reset }: {
  result: Analysis; review: TransferReview; session: Session | null; sample: boolean;
  heading: RefObject<HTMLHeadingElement | null>; reset: () => void;
}) {
  const { status } = review;
  const conflict = status === "conflict";
  const payment = status === "payment";
  const suspicious = result.risk_level === "high" || result.risk_level === "medium";
  const needsVerification = !payment || result.risk_level !== "low";
  const amount = review.amount ? Number(review.amount).toLocaleString("vi-VN") + " ₫" : null;
  const findings = result.evidence.filter(item => item.weight > 0 && item.finding !== result.brand_alert?.finding &&
    !(conflict && item.source === "vietqr" && item.weight === 45));
  return <section className="panel page-panel transfer-result" data-tone={conflict || suspicious ? "warning" : needsVerification ? "unknown" : "payment"}
    aria-labelledby="transfer-result-heading">
    <div className="transfer-outcome">
      {needsVerification ? <AlertTriangle size={26} aria-hidden="true" /> : <ShieldCheck size={26} aria-hidden="true" />}
      <div className="stack">
        <h2 id="transfer-result-heading" tabIndex={-1} ref={heading}>
          {conflict ? "Bạn đang chờ nhận tiền" : payment ? "Đây là mã chuyển tiền đi" : "Cần xác minh mã QR"}
        </h2>
        {conflict ? <p className="transfer-direction">{amount ? `Nếu xác nhận, bạn sẽ chuyển đi ${amount}.` : "Nếu xác nhận, tiền sẽ được chuyển đi. Mã chưa đặt số tiền."}</p>
          : payment ? <p>{amount ? `Mã yêu cầu chuyển ${amount} đến tài khoản bên dưới.` : "Mã chưa đặt số tiền. Hãy kiểm tra số tiền và người nhận."}</p>
          : <p>{unknownDetails[status]}</p>}
      </div>
    </div>
    {result.brand_alert && <BrandNotice alert={result.brand_alert} />}
    {(conflict || payment) && <dl className="qr-data">
      <div><dt>Ngân hàng trong mã</dt><dd>{review.bank || "Chưa xác định"}</dd></div>
      <div><dt>Tài khoản trong mã</dt><dd>{review.account}</dd></div>
    </dl>}
    {review.quote && <div className="transfer-quote">
      <p className="micro muted">{review.quote_source === "image" ? "Cụm từ đọc từ ảnh" : "Cụm từ trong tin nhắn"}</p>
      <blockquote>“{review.quote}”</blockquote>
    </div>}
    {result.image_reader === "qwen4-max" && <p className="micro muted">Qwen đã đọc chữ trong ảnh.</p>}
    {result.image_reader === "local_ocr_fallback" && <p className="micro muted">Ảnh được đọc chữ bằng OCR cục bộ.</p>}
    {suspicious && (findings.length > 0 || result.red_flags.length > 0) && <ul className="flag-list">
      {findings.map((item, index) => <li key={item.source + index}>{item.finding}</li>)}
      {result.red_flags.map(flag => <li key={flag.quote + flag.reason}><blockquote>“{flag.quote}”</blockquote><p>{flag.reason}</p></li>)}
    </ul>}
    {needsVerification ? <details className="transfer-verify">
      <summary className="button primary">Dừng để xác minh</summary>
      <div className="stack transfer-support">
        <SupportLinks />
        <ResultActions analysisId={result.analysis_id} initialSession={session} previewShare canReport={!sample} />
      </div>
    </details> : <div className="actions"><button className="button secondary" type="button" onClick={reset}>Quay lại kiểm tra</button></div>}
    {(conflict || payment) && <p className="micro muted">Thông tin lấy từ mã QR. Danh tính người nhận cần được xác minh qua kênh chính thức.</p>}
  </section>;
}
