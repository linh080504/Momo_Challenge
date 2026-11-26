"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useRef, useState, type FormEvent } from "react";
import { ImagePlus, MessageCircleMore, ScanLine, Send, Sparkles, X } from "lucide-react";
import { analyze, riskLabels, type Analysis } from "@/lib/api";
import { BrandMascot } from "@/components/brand";
import "./quick-chat.css";

const example = "Ưu đãi Black Friday sắp hết hạn. Hãy gửi mã OTP cho shop để xác nhận và chuyển ngay tiền đặt cọc.";

type Turn = { id: number; text: string; result?: Analysis; error?: string };

export function QuickChat() {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [progress, setProgress] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);
  const nextTurn = useRef(0);
  const launcher = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const log = useRef<HTMLDivElement>(null);

  const close = useCallback(() => {
    setOpen(false);
    launcher.current?.focus({ preventScroll: true });
  }, []);

  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (!open) return;
    panel.current?.focus({ preventScroll: true });
    function onEscape(event: KeyboardEvent) {
      if (event.key === "Escape" && !event.isComposing && !event.defaultPrevented) close();
    }
    document.addEventListener("keydown", onEscape);
    return () => document.removeEventListener("keydown", onEscape);
  }, [open, close]);
  useEffect(() => {
    if (open && log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [open, turns, progress]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || request.current) return;

    const turnId = ++nextTurn.current;
    setTurns(previous => [...previous.slice(-5), { id: turnId, text }]);
    setDraft("");
    setProgress("Đang kiểm tra nội dung…");
    const controller = new AbortController();
    request.current = controller;
    const timeout = window.setTimeout(() => controller.abort("timeout"), 20000);
    let outcome: Pick<Turn, "result" | "error"> | undefined;

    try {
      const result = await analyze({ text }, step => setProgress(step.message), undefined, controller.signal);
      outcome = { result };
    } catch (failure) {
      if (controller.signal.reason === "timeout") outcome = { error: "Kiểm tra mất nhiều thời gian. Hãy gửi lại nội dung." };
      else if (!controller.signal.aborted) outcome = {
        error: failure instanceof Error ? failure.message : "Bạn có thể gửi lại để kiểm tra.",
      };
    } finally {
      window.clearTimeout(timeout);
      request.current = null;
    }
    if (outcome) {
      setTurns(previous => previous.map(turn => turn.id === turnId ? { ...turn, ...outcome } : turn));
      setProgress(null);
    }
  }

  return (
    <div className="quick-chat">
      {open && <section id={id} ref={panel} className="quick-chat-panel" role="dialog"
        aria-labelledby={id + "-title"} tabIndex={-1}>
        <header className="quick-chat-header">
          <span className="quick-chat-avatar"><BrandMascot size={48} /></span>
          <div>
            <h2 id={id + "-title"}>Trợ lý kiểm tra</h2>
            <p>Tin nhắn và đường link</p>
          </div>
          <button type="button" className="quick-chat-close" aria-label="Đóng khung chat" onClick={close}>
            <X size={21} aria-hidden="true" />
          </button>
        </header>

        <div className="quick-chat-log" ref={log} role="log" aria-label="Nội dung kiểm tra">
          <p className="quick-chat-bubble chat-intro">Dán tin nhắn hoặc link bạn nghi ngờ để xem dấu hiệu cần xác minh.</p>
          <div className="quick-chat-shortcuts">
            <button type="button" onClick={() => { setDraft(example); input.current?.focus(); }}>
              <Sparkles size={15} aria-hidden="true" />Dùng mẫu
            </button>
            <a href="#kiem-tra" onClick={() => setOpen(false)}><ImagePlus size={15} aria-hidden="true" />Ảnh chụp</a>
            <Link href="/qr"><ScanLine size={15} aria-hidden="true" />VietQR</Link>
          </div>
          {turns.map(turn => (
            <div key={turn.id} className="quick-chat-turn">
              <p className="quick-chat-bubble chat-user">{turn.text}</p>
              {turn.error && <p className="quick-chat-bubble chat-error" role="alert">{turn.error}</p>}
              {turn.result && <div className="quick-chat-bubble chat-result">
                <span className={"chat-risk risk-" + turn.result.risk_level}>{riskLabels[turn.result.risk_level]}</span>
                <p>{turn.result.summary}</p>
                {turn.result.red_flags[0] && <blockquote>“{turn.result.red_flags[0].quote}”</blockquote>}
                {turn.result.verification_questions[0] && <p>{turn.result.verification_questions[0]}</p>}
                <small>{turn.result.ai_disclaimer}</small>
              </div>}
            </div>
          ))}
          {progress && <p className="quick-chat-bubble chat-progress" role="status">{progress}</p>}
        </div>

        <form className="quick-chat-composer" onSubmit={submit}>
          <div className="quick-chat-entry">
            <textarea ref={input} value={draft} onChange={event => setDraft(event.target.value)}
              aria-label="Tin nhắn cần kiểm tra" aria-describedby={id + "-hint"} rows={2}
              maxLength={12000} placeholder="Dán nội dung cần kiểm tra…" />
            <button type="submit" aria-label="Gửi để kiểm tra" disabled={!!progress || !draft.trim()}>
              <Send size={19} aria-hidden="true" />
            </button>
          </div>
          <small id={id + "-hint"}>Che mã OTP và mật khẩu trước khi gửi.</small>
        </form>
      </section>}

      <button type="button" ref={launcher} className="quick-chat-launcher"
        aria-label={open ? "Thu gọn trợ lý kiểm tra" : "Mở trợ lý kiểm tra"}
        aria-expanded={open} aria-controls={open ? id : undefined} data-open={open}
        onClick={() => { if (open) close(); else setOpen(true); }}>
        {open ? <X size={26} aria-hidden="true" /> : <>
          <BrandMascot size={61} />
          <span className="quick-chat-mark"><MessageCircleMore size={16} aria-hidden="true" /></span>
        </>}
      </button>
    </div>
  );
}
