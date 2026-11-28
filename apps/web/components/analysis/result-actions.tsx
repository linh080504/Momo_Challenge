"use client";

import { useState } from "react";
import { Check, Flag, LockKeyhole, Share2 } from "lucide-react";
import { api, ApiError, riskLabels, saveSession, type Risk, type Session } from "@/lib/api";
import { projectName } from "@/components/brand";
import { LoginForm } from "@/components/login-form";

type SharedPreview = { risk: Risk; summary: string; disclaimer: string };

export function ResultActions({ analysisId, initialSession, previewShare = false, canReport = true }: {
  analysisId: string; initialSession: Session | null; previewShare?: boolean; canReport?: boolean;
}) {
  const [session, setSession] = useState(initialSession);
  const [signingIn, setSigningIn] = useState(false);
  const [reported, setReported] = useState(false);
  const [pending, setPending] = useState<"report" | "share" | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [shareUrl, setShareUrl] = useState("");
  const [preview, setPreview] = useState<SharedPreview>();

  async function report(activeSession: Session) {
    setPending("report");
    setError("");
    try {
      await api("/v1/reports", "POST", { analysis_id: analysisId, consent: true }, activeSession.token);
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
      const { token } = await api<{ token: string }>("/v1/shares", "POST", { analysis_id: analysisId }, session?.token);
      const url = new URL("/share/" + encodeURIComponent(token), window.location.origin).toString();
      if (previewShare) setPreview(await api<SharedPreview>("/v1/shares/" + encodeURIComponent(token)));
      setShareUrl(url);
      if (!previewShare) await sendLink(url);
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setPending(null);
    }
  }

  async function sendLink(url: string) {
    try {
      if (navigator.share) await navigator.share({ title: projectName, url });
      else if (navigator.clipboard) {
        await navigator.clipboard.writeText(url);
        setMessage("Đã sao chép liên kết.");
      } else setMessage("Bạn có thể sao chép liên kết bên dưới.");
    } catch (failure) {
      if ((failure as Error).name !== "AbortError") setMessage("Bạn có thể sao chép liên kết bên dưới.");
    }
  }

  return <>
    <div className="actions">
      {canReport && <button type="button" className="button primary" disabled={reported || pending !== null}
        onClick={() => session ? void report(session) : setSigningIn(true)}>
        {reported ? <Check size={19} /> : <Flag size={19} />}
        {reported ? "Đã báo cáo" : pending === "report" ? "Đang gửi…" : previewShare ? "Báo cáo cho PayPause" : "Báo cáo"}
      </button>}
      <button type="button" className="button secondary" disabled={pending !== null} onClick={share}><Share2 size={18} />
        {pending === "share" ? "Đang tạo liên kết…" : "Hỏi người thân"}
      </button>
    </div>
    {canReport && <p className="micro muted"><LockKeyhole size={15} /> Khi báo cáo, bạn đồng ý gửi tín hiệu và mã đối chiếu đã che cho đội vận hành.</p>}
    {signingIn && <div className="inline-login">
      <h3>Đăng nhập để gửi báo cáo</h3>
      <LoginForm button="Đăng nhập và báo cáo" onSignedIn={active => {
        setSession(active);
        void report(active);
      }} />
    </div>}
    {error && <p role="alert" className="error">{error}</p>}
    {message && <p role="status" className="muted">{message}</p>}
    {shareUrl && <div className={preview ? "panel page-panel" : undefined}>
      {preview && <>
        <h3>Người thân sẽ thấy</h3>
        <p><span className={"badge risk-" + preview.risk}>{riskLabels[preview.risk]}</span></p>
        <p>{preview.summary}</p>
        <p className="disclaimer">{preview.disclaimer}</p>
      </>}
      <label>Liên kết đã che thông tin, có hiệu lực 24 giờ
        <input readOnly value={shareUrl} onFocus={event => event.target.select()} />
      </label>
      {preview && <div className="actions"><button type="button" className="button secondary" onClick={() => void sendLink(shareUrl)}>
        <Share2 size={18} /> Chia sẻ liên kết
      </button></div>}
    </div>}
  </>;
}
