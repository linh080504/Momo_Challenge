"use client";

import { useState, type FormEvent } from "react";
import { LockKeyhole } from "lucide-react";
import { api, saveSession, type Session } from "@/lib/api";

export function LoginForm({ onSignedIn, button = "Đăng nhập" }: {
  onSignedIn: (session: Session) => void;
  button?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const session = await api<Session>("/v1/auth/login", "POST", {
        email: data.get("email"), password: data.get("password"),
      });
      saveSession(session);
      onSignedIn(session);
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return <form onSubmit={submit} className="stack">
    <label>Email<input name="email" type="email" autoComplete="username" required /></label>
    <label>Mật khẩu<input name="password" type="password" autoComplete="current-password" required /></label>
    {error && <p role="alert" className="error">{error}</p>}
    <button className="button primary" disabled={busy}><LockKeyhole size={19} />{busy ? "Đang đăng nhập…" : button}</button>
  </form>;
}
