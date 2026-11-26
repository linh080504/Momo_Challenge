"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { CheckCircle2, ClipboardList, LoaderCircle, Search, Sparkles } from "lucide-react";
import { analyze, ApiError, currentSession, entityLabels, saveSession, type Analysis, type AnalysisEvent, type Input, type Session } from "@/lib/api";
import { audioInput } from "@/lib/audio";
import { imageInput, receiptInput } from "@/lib/images";
import { Result } from "./result";
import { Upload } from "./upload";

const SAMPLE = "Tôi là cán bộ công an. Hãy chuyển ngay vào tài khoản tạm giữ để xác minh, không được nói với ai.";

export function AnalyzerForm() {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<"image" | "receipt" | "audio">("image");
  const [events, setEvents] = useState<AnalysisEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Analysis | null>(null);
  const [receipt, setReceipt] = useState<File | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const active = useRef<AbortController | null>(null);
  const resultElement = useRef<HTMLDivElement>(null);

  useEffect(() => () => active.current?.abort(), []);
  useEffect(() => { if (result) resultElement.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [result]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !(text.trim() || file)) return;
    setBusy(true);
    setError("");
    setEvents([]);
    setResult(null);
    const controller = new AbortController();
    active.current = controller;
    const timeout = window.setTimeout(() => controller.abort("timeout"), mode === "audio" ? 35000 : 20000);
    try {
      const input: Input = { text: text.trim() };
      if (file && mode === "audio") {
        input.audio_base64 = await audioInput(file);
      } else if (file && mode === "receipt") {
        input.image_kind = "receipt";
        input.image_mime = file.type;
        input.image_base64 = await receiptInput(file);
      } else if (file) {
        Object.assign(input, await imageInput(file));
      }
      let signedIn = currentSession();
      let analysis: Analysis;
      try {
        analysis = await analyze(input, item => setEvents(steps => [...steps, item]), signedIn?.token, controller.signal);
      } catch (failure) {
        if (!(failure instanceof ApiError && failure.status === 401 && signedIn)) throw failure;
        signedIn = null;
        saveSession(null);
        analysis = await analyze(input, item => setEvents(steps => [...steps, item]), undefined, controller.signal);
      }
      setSession(signedIn);
      setReceipt(mode === "receipt" ? file : null);
      setResult(analysis);
    } catch (failure) {
      if (controller.signal.reason === "timeout") setError("Phân tích mất nhiều thời gian. Hãy thử lại.");
      else if (!controller.signal.aborted) setError((failure as Error).message);
    } finally {
      window.clearTimeout(timeout);
      active.current = null;
      setBusy(false);
    }
  }

  return (
    <div className="form-column">
      <section className="panel input-panel" aria-labelledby="checker-title">
        <div className="panel-heading">
          <span className="heading-icon"><ClipboardList size={22} aria-hidden="true" /></span>
          <h2 id="checker-title">Nội dung cần kiểm tra</h2>
        </div>
        <form onSubmit={submit} className="checker-form">
          <div className="input-caption">
            <label htmlFor="input-text">Tin nhắn hoặc đường link</label>
            <button type="button" className="sample-button" onClick={() => { setText(SAMPLE); setFile(null); }} disabled={busy}>
              <Sparkles size={16} aria-hidden="true" />Dùng mẫu
            </button>
          </div>
          <div className="text-field">
            <textarea id="input-text" value={text} maxLength={12000} disabled={busy}
              onChange={event => setText(event.target.value)}
              onPaste={event => {
                const image = Array.from(event.clipboardData.files)[0];
                if (image?.type.startsWith("image/")) {
                  event.preventDefault();
                  if (mode === "audio") setMode("image");
                  setFile(image);
                }
              }}
              placeholder="Dán nội dung bạn nhận được vào đây…" aria-describedby="input-count" />
            <span id="input-count" className="form-meta">{text.length.toLocaleString("vi-VN")} / 12.000</span>
          </div>
          <label>Loại tệp đính kèm
            <select value={mode} disabled={busy} onChange={event => {
              setMode(event.target.value as typeof mode);
              setFile(null);
            }}>
              <option value="image">Ảnh chụp tin nhắn</option>
              <option value="receipt">Biên lai giao dịch</option>
              <option value="audio">Ghi âm</option>
            </select>
          </label>
          <Upload file={file} onChange={setFile} disabled={busy} mode={mode} />
          {error && <p role="alert" className="error">{error}</p>}
          <button className="button primary check-button" disabled={busy || !(text.trim() || file)}>
            {busy ? <LoaderCircle size={21} className="spinning" /> : <Search size={21} />}
            {busy ? "Đang kiểm tra…" : "Kiểm tra ngay"}
          </button>
        </form>
        {busy && <div role="status" className="progress">
          {events.length === 0 && <p>{file ? "Đang đọc tệp đính kèm…" : "Đang tiếp nhận nội dung…"}</p>}
          {events.map(step => <div key={step.stage} className="progress-step">
            {step.stage === "evidence" ? <LoaderCircle size={18} className="spinning" aria-hidden="true" /> :
              <CheckCircle2 size={18} aria-hidden="true" />}
            <div>{step.message}
              {step.entities && step.entities.length > 0 && <span className="progress-entities">{step.entities.slice(0, 3).map((entity, index) =>
                <span key={index}>{entityLabels[entity.type] || entity.type} {entity.type === "URL" ? "" : entity.display}</span>
              )}</span>}</div>
          </div>)}
        </div>}
      </section>
      {result && <div ref={resultElement}><Result key={result.analysis_id} result={result} initialSession={session} receipt={receipt} /></div>}
    </div>
  );
}
