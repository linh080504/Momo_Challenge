"use client";

import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { CheckCircle2, ClipboardList, Globe2, LoaderCircle, ScanEye, Search, Sparkles } from "lucide-react";
import { analyze, ApiError, currentSession, entityLabels, saveSession, type Analysis, type AnalysisEvent, type Input, type Session } from "@/lib/api";
import { audioInput } from "@/lib/audio";
import { type AnalyzerDraft, type AnalyzerKind } from "@/lib/check-draft";
import { imageInput, receiptInput } from "@/lib/images";
import { Result } from "./result";
import { Upload } from "./upload";
import { LiveTab } from "./live-tab";
import { WebsiteSnapshot } from "./website-snapshot";

const SAMPLE = "Tôi là cán bộ công an. Hãy chuyển ngay vào tài khoản tạm giữ để xác minh, không được nói với ai.";

export function AnalyzerForm({ kind = "website", compact = false, initialDraft, onCheck }: {
  kind?: AnalyzerKind;
  compact?: boolean;
  initialDraft?: AnalyzerDraft;
  onCheck?: (draft: AnalyzerDraft) => void;
}) {
  const website = kind === "website";
  const screenshot = kind === "image";
  const mediaMode = kind === "image" || kind === "receipt" || kind === "audio" ? kind : null;
  const headingId = useId();
  const [text, setText] = useState(initialDraft?.text ?? "");
  const [markup, setMarkup] = useState(initialDraft?.markup ?? "");
  const [file, setFile] = useState<File | null>(initialDraft?.file ?? null);
  const [events, setEvents] = useState<AnalysisEvent[]>([]);
  const [capture, setCapture] = useState<AnalysisEvent["website_capture"]>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Analysis | null>(null);
  const [receipt, setReceipt] = useState<File | null>(null);
  const [websiteImage, setWebsiteImage] = useState<File | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const active = useRef<AbortController | null>(null);
  const lastWebsiteInput = useRef<Input | null>(null);
  const formElement = useRef<HTMLFormElement>(null);
  const resultElement = useRef<HTMLDivElement>(null);
  const captureElement = useRef<HTMLElement>(null);
  const capturePicture = capture ? `data:image/jpeg;base64,${capture.jpeg}` : undefined;
  const canSubmit = mediaMode && kind !== "audio" ? Boolean(file) :
    Boolean(text.trim() || (kind === "audio" && file));

  useEffect(() => () => active.current?.abort(), []);
  useEffect(() => {
    if (!initialDraft) return;
    const timer = window.setTimeout(() => formElement.current?.requestSubmit(), 0);
    return () => window.clearTimeout(timer);
  }, [initialDraft]);
  useEffect(() => { if (result) resultElement.current?.scrollIntoView({ behavior: "smooth", block: website ? "start" : "nearest" }); }, [result, website]);
  useEffect(() => { if (busy && capturePicture) captureElement.current?.scrollIntoView({ block: "start" }); }, [busy, capturePicture]);

  function updateProgress(item: AnalysisEvent) {
    if (item.website_capture) setCapture(item.website_capture);
    setEvents(steps => [...steps, item]);
  }

  async function runAnalysis(savedInput?: Input) {
    if (active.current || (!savedInput && !canSubmit)) return;
    setBusy(true);
    setError("");
    setEvents([]);
    setCapture(undefined);
    if (!savedInput) setResult(null);
    const controller = new AbortController();
    active.current = controller;
    const timeout = window.setTimeout(() => controller.abort("timeout"),
      website || screenshot ? 45000 : kind === "audio" ? 35000 : 20000);
    try {
      let input = savedInput;
      if (!input) {
        input = website ? { url: text.trim(), text: "", website_preview: true } : { text: text.trim() };
        if (website && markup.trim()) input.website_html = markup.trim();
        if (file && kind === "audio") {
          input.audio_base64 = await audioInput(file);
        } else if (file && kind === "receipt") {
          input.image_kind = "receipt";
          input.image_mime = file.type;
          input.image_base64 = await receiptInput(file);
        } else if (file) {
          Object.assign(input, await imageInput(file));
          if (screenshot || website) input.qwen_vision = true;
        }
      }
      let signedIn = currentSession();
      let analysis: Analysis;
      try {
        analysis = await analyze(input, updateProgress, signedIn?.token, controller.signal);
      } catch (failure) {
        if (!(failure instanceof ApiError && failure.status === 401 && signedIn)) throw failure;
        signedIn = null;
        saveSession(null);
        analysis = await analyze(input, updateProgress, undefined, controller.signal);
      }
      setSession(signedIn);
      if (!savedInput) {
        setReceipt(kind === "receipt" ? file : null);
        setWebsiteImage(website ? file : null);
      }
      if (website) lastWebsiteInput.current = input;
      setResult(analysis);
    } catch (failure) {
      if (controller.signal.reason === "timeout") setError("Phân tích mất nhiều thời gian. Hãy thử lại.");
      else if (!controller.signal.aborted) setError((failure as Error).message);
    } finally {
      window.clearTimeout(timeout);
      active.current = null;
      setBusy(false);
      setCapture(undefined);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    if (onCheck) {
      onCheck({ kind, text, markup, file });
      return;
    }
    void runAnalysis();
  }

  function reanalyze() {
    if (lastWebsiteInput.current) void runAnalysis(lastWebsiteInput.current);
  }

  const websiteEvidence = website && <>
    <details className="details" open={file ? true : undefined}>
      <summary>Thêm bằng chứng từ ảnh hoặc tab</summary>
      <Upload file={file} onChange={setFile} disabled={busy} />
      <p className="micro muted">Khi bấm phân tích, ảnh đính kèm được gửi đến QwenCloud để đọc chữ. Hãy che thông tin riêng tư trước khi gửi.</p>
      <LiveTab disabled={busy} onCapture={setFile} />
    </details>
    <details className="details">
      <summary>Thêm đoạn mã HTML có sẵn</summary>
      <label>Mã nguồn HTML
        <textarea value={markup} onChange={event => setMarkup(event.target.value)}
          maxLength={35000} disabled={busy} spellCheck={false} aria-describedby="website-html-hint" />
      </label>
      <p id="website-html-hint" className="micro muted">Chỉ dán đoạn HTML đã bỏ thông tin cá nhân. Hệ thống chỉ đọc mã, không chạy trang.</p>
    </details>
  </>;

  return (
    <div className="form-column">
      <section className="panel input-panel" aria-labelledby={compact ? undefined : headingId}>
        {!compact && <div className="panel-heading">
          <span className="heading-icon">{website ? <Globe2 size={22} aria-hidden="true" /> : <ClipboardList size={22} aria-hidden="true" />}</span>
          <h2 id={headingId}>{website ? "Địa chỉ website" : "Nội dung cần kiểm tra"}</h2>
        </div>}
        <form ref={formElement} onSubmit={submit} className={website
          ? compact ? "checker-form compact-website-form" : "checker-form website-url-form"
          : "checker-form"}>
          {website ? <>
            <label htmlFor="website-url">Link cần kiểm tra</label>
            <input id="website-url" type="text" inputMode="url" autoComplete="off" spellCheck={false} maxLength={2000}
              value={text} onChange={event => setText(event.target.value)} disabled={busy} required placeholder="https://example.com" />
          </> : kind === "text" && <>
          <div className="input-caption">
            <label htmlFor="input-text">Tin nhắn cần kiểm tra</label>
            <button type="button" className="sample-button" onClick={() => setText(SAMPLE)} disabled={busy}>
              <Sparkles size={16} aria-hidden="true" />Dùng mẫu
            </button>
          </div>
          <div className="text-field">
            <textarea id="input-text" value={text} maxLength={12000} disabled={busy}
              onChange={event => setText(event.target.value)}
              placeholder="Dán nội dung bạn nhận được vào đây…" aria-describedby="input-count" />
            <span id="input-count" className="form-meta">{text.length.toLocaleString("vi-VN")} / 12.000</span>
          </div>
          </>}
          {mediaMode && <>
            <Upload file={file} onChange={setFile} disabled={busy} mode={mediaMode} />
            <details className="details">
              <summary>{kind === "audio" ? "Dán lời thoại hoặc thêm ngữ cảnh" : "Thêm nội dung đi kèm"}</summary>
              <label>{kind === "audio" ? "Lời thoại hoặc nội dung đi kèm" : "Tin nhắn đi kèm (tùy chọn)"}
                <textarea value={text} maxLength={12000} disabled={busy}
                  onChange={event => setText(event.target.value)} rows={2} />
              </label>
              {kind === "audio" && <p className="muted micro">Nếu phiên âm gặp lỗi, hãy gỡ tệp và kiểm tra bằng phần lời bạn đã chép.</p>}
            </details>
          </>}
          {!compact && websiteEvidence}
          {error && !result && <p role="alert" className="error">{error}</p>}
          {screenshot && <p id={headingId + "-qwen"} className="micro muted">
            Khi bấm kiểm tra, ảnh được gửi tới QwenCloud để đọc và phân tích. Hãy che thông tin cá nhân trước khi gửi.
          </p>}
          <button type="submit" className="button primary check-button"
            aria-describedby={screenshot ? headingId + "-qwen" : undefined} disabled={busy || !canSubmit}>
            {busy ? <LoaderCircle size={21} className="spinning" /> : <Search size={21} />}
            {busy ? "Đang kiểm tra…" : website ? "Phân tích website" : "Kiểm tra ngay"}
          </button>
          {compact && websiteEvidence && <details className="details">
            <summary>Bổ sung bằng chứng (tùy chọn)</summary>
            {websiteEvidence}
          </details>}
        </form>
        {busy && <div role="status" className="progress">
          {events.length === 0 && <p>{file ? "Đang đọc tệp đính kèm…" : "Đang tiếp nhận nội dung…"}</p>}
          {events.map(step => <div key={step.stage} className="progress-step">
            {step.stage === events.at(-1)?.stage ? <LoaderCircle size={18} className="spinning" aria-hidden="true" /> :
              <CheckCircle2 size={18} aria-hidden="true" />}
            <div>{step.message}
              {step.entities && step.entities.length > 0 && <span className="progress-entities">{step.entities.slice(0, 3).map((entity, index) =>
                <span key={index}>{entityLabels[entity.type] || entity.type} {entity.type === "URL" ? "" : entity.display}</span>
              )}</span>}</div>
          </div>)}
        </div>}
      </section>
      {busy && website && !result && <section ref={captureElement} className="website-report-block website-visual website-result-anchor">
        <h3><ScanEye size={21} aria-hidden="true" /> Hình ảnh website</h3>
        <WebsiteSnapshot picture={capturePicture} host={capture?.host} />
      </section>}
      {result && <div ref={resultElement} className={website ? "website-result-anchor" : undefined}>
        <Result key={result.analysis_id} result={result} initialSession={session} receipt={receipt} websiteImage={websiteImage}
          websiteRefresh={website ? { busy, picture: capturePicture, error, run: reanalyze } : undefined} />
      </div>}
    </div>
  );
}
