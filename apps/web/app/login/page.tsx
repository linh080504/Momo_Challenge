"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { LogOut, ShieldCheck, Trash2 } from "lucide-react";
import { LoginForm } from "@/components/login-form";
import { api, ApiError, currentSession, saveSession, type Account, type Session } from "@/lib/api";

export default function AccountPage() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const saved = currentSession();
    // The browser session can only be read after hydration.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (!saved) { setLoading(false); return; }
    const controller = new AbortController();
    api<Account>("/v1/auth/me", "GET", undefined, saved.token, controller.signal)
      .then(account => setSession({ ...account, token: saved.token }))
      .catch(failure => {
        if (controller.signal.aborted) return;
        if (failure instanceof ApiError && failure.status === 401) saveSession(null);
        else setError((failure as Error).message);
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  async function action(kind: "logout" | "erase") {
    if (!session) return;
    setWorking(true);
    setError("");
    setMessage("");
    try {
      if (kind === "logout") {
        await api("/v1/auth/session", "DELETE", undefined, session.token);
        saveSession(null);
        setSession(null);
      } else {
        const result = await api<{ deleted: number }>("/v1/me/reports", "DELETE", undefined, session.token);
        setMessage("Đã xóa " + result.deleted + " báo cáo của bạn.");
        setConfirmDelete(false);
      }
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) {
        saveSession(null);
        setSession(null);
      }
      setError((failure as Error).message);
    } finally {
      setWorking(false);
    }
  }

  return <div className="narrow page-section">
    <section className="panel page-panel">
      <span className="heading-icon"><ShieldCheck size={23} /></span>
      <h1>Tài khoản</h1>
      {loading ? <p role="status">Đang kiểm tra phiên đăng nhập…</p> : session ?
        <div className="stack">
          <p><strong>{session.email}</strong><br /><span className="muted">{session.role === "ops" ? "Chuyên viên vận hành" : "Người dùng"}</span></p>
          {session.role === "ops" ? <Link href="/ops" className="button primary">Mở bàn làm việc</Link> :
            <Link href="/" className="button primary">Kiểm tra tin nhắn</Link>}
          {confirmDelete && <p>Báo cáo của bạn sẽ được xóa khỏi hệ thống. Quyết định duyệt vẫn có trong nhật ký vận hành.</p>}
          <div className="actions">
            <button type="button" className="button secondary" disabled={working} onClick={() => void action("logout")}><LogOut size={18} />Đăng xuất</button>
            <button type="button" className="button secondary" disabled={working}
              onClick={() => confirmDelete ? void action("erase") : setConfirmDelete(true)}><Trash2 size={18} />
              {confirmDelete ? "Xác nhận xóa báo cáo" : "Xóa báo cáo của tôi"}
            </button>
            {confirmDelete && <button className="text-button" onClick={() => setConfirmDelete(false)}>Quay lại</button>}
          </div>
        </div> : <LoginForm onSignedIn={setSession} />}
      {message && <p role="status">{message}</p>}
      {error && <p role="alert" className="error">{error}</p>}
    </section>
  </div>;
}
