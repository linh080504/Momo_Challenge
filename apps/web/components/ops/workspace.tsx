"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { Check, Inbox, LayoutGrid, RefreshCw, X } from "lucide-react";
import { LoginForm } from "@/components/login-form";
import { InvestigationWorkspace } from "./investigation";
import {
  api, ApiError, currentSession, entityLabels, riskLabels, saveSession,
  type Campaign, type CampaignState, type Session,
} from "@/lib/api";

const labels: Record<CampaignState, string> = { pending: "Chờ duyệt", approved: "Đã duyệt", rejected: "Đã bác bỏ" };
const groups = {
  G1: "Mạo danh cơ quan, tổ chức", G2: "Mạo danh người quen", G3: "Đầu tư hoặc tuyển dụng",
  G4: "Mua bán và giao dịch trực tuyến", G5: "Đánh cắp dữ liệu hoặc tài khoản",
};
const historyLabels = { approve: "Duyệt", reject: "Bác bỏ", edit_group: "Cập nhật phân loại" };
const filters: CampaignState[] = ["pending", "approved", "rejected"];
const formatDate = (seconds: number) => new Date(seconds * 1000).toLocaleString("vi-VN");

export function Workspace({ campaignId }: { campaignId?: string }) {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [state, setState] = useState<CampaignState>("pending");
  const [campaigns, setCampaigns] = useState<Campaign[] | null>(null);
  const [detail, setDetail] = useState<Campaign | null>(null);
  const [reload, setReload] = useState(0);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  // Browser session storage is available only after hydration.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setSession(currentSession()); setReady(true); }, []);

  useEffect(() => {
    if (session?.role !== "ops") return;
    const controller = new AbortController();
    // Clear stale results as soon as the selected query changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setError("");
    setCampaigns(null);
    setDetail(null);
    const options = ["GET", undefined, session.token, controller.signal] as const;
    const fetchData = campaignId
      ? api<Campaign>("/v1/ops/campaigns/" + encodeURIComponent(campaignId), ...options).then(setDetail)
      : api<Campaign[]>("/v1/ops/campaigns?state=" + state, ...options).then(setCampaigns);
    fetchData.catch(failure => {
      if (controller.signal.aborted) return;
      if (failure instanceof ApiError && (failure.status === 401 || failure.status === 403)) {
        saveSession(null);
        setSession(null);
      }
      setError((failure as Error).message);
    });
    return () => controller.abort();
  }, [campaignId, reload, session, state]);

  async function decide(decision: "approve" | "reject") {
    if (!session || !detail || working) return;
    setWorking(true);
    setError("");
    try {
      setDetail(await api<Campaign>("/v1/ops/campaigns/" + detail.id + "/decision", "POST",
        { decision, revision: detail.revision }, session.token));
      setReload(value => value + 1);
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setWorking(false);
    }
  }

  async function edit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !detail || working) return;
    const group = new FormData(event.currentTarget).get("group");
    setWorking(true);
    setError("");
    try {
      setDetail(await api<Campaign>("/v1/ops/campaigns/" + detail.id + "/review", "POST",
        { group, revision: detail.revision }, session.token));
      setReload(value => value + 1);
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setWorking(false);
    }
  }

  if (!ready) return <p role="status" className="page-section">Đang mở bàn làm việc…</p>;
  if (session?.role !== "ops") return <div className="narrow page-section"><section className="panel page-panel">
    <span className="heading-icon"><LayoutGrid size={23} /></span><h1>Bàn làm việc vận hành</h1>
    <p className="muted">Đăng nhập bằng tài khoản vận hành để xem và duyệt các chiến dịch báo cáo.</p>
    {error && <p role="alert" className="error">{error}</p>}
    <LoginForm onSignedIn={active => {
      setSession(active);
      setError(active.role === "ops" ? "" : "Tài khoản này chưa có quyền vận hành.");
    }} />
  </section></div>;

  return (
    <div className="page-section">
      <div className="page-heading">
        <div>
          {campaignId && <Link href="/ops" className="breadcrumb">Bàn làm việc vận hành</Link>}
          <h1>{campaignId ? "Chi tiết chiến dịch" : "Chiến dịch báo cáo"}</h1>
          {!campaignId && <p>Đối chiếu bằng chứng và duyệt cảnh báo từ báo cáo của người dùng.</p>}
        </div>
        <button type="button" className="button secondary" disabled={working} onClick={() => setReload(value => value + 1)}><RefreshCw size={18} />Tải lại</button>
      </div>
      {error && <p role="alert" className="error">{error}</p>}
      {campaignId ? detail ? <section className="panel page-panel campaign-details">
        <div className="chips"><span className={"badge risk-" + detail.risk}>{riskLabels[detail.risk]}</span><span className="chip">{labels[detail.state]}</span></div>
        <h2>{detail.title}</h2>
        <p className="muted">Mã {detail.id.slice(0, 8).toUpperCase()} · {formatDate(detail.created)}</p>
        <p>{detail.summary}</p>
        {detail.workspace && <InvestigationWorkspace workspace={detail.workspace} />}
        <h3>Thông tin đối chiếu</h3>
        <p>{Object.entries(detail.entities).map(([kind, count]) => count + " " + (entityLabels[kind]?.toLowerCase() || kind)).join(" · ") || "Chưa có thực thể dùng để đối chiếu."}</p>
        <h3>Bằng chứng từ báo cáo</h3>
        {detail.signals.length ? <ul className="question-list">{detail.signals.map(signal => <li key={signal}>{signal}</li>)}</ul> :
          <p className="muted">Chưa có tín hiệu được ghi nhận.</p>}
        <h3>Nhật ký quyết định</h3>
        {detail.history.length ? <ul className="question-list">{detail.history.map((item, index) =>
          <li key={index}>{historyLabels[item.action]} bởi {item.actor} · {formatDate(item.created)}</li>)}</ul> :
          <p className="muted">Đang chờ chuyên viên quyết định.</p>}
        {detail.state === "pending" && <details className="details">
          <summary>Sửa nhóm thủ đoạn</summary>
          <form className="stack" onSubmit={edit} key={detail.revision}>
            <label>Nhóm thủ đoạn
              <select name="group" required defaultValue={detail.group || ""}>
                <option value="" disabled>Chọn nhóm</option>
                {Object.entries(groups).map(([key, value]) => <option key={key} value={key}>{value}</option>)}
              </select>
            </label>
            <button className="button secondary" disabled={working}>Lưu nhóm thủ đoạn</button>
          </form>
        </details>}
        {detail.state === "pending" && <div className="review">
          <p className="muted">Khi duyệt, các lần kiểm tra trùng thông tin sẽ hiển thị cảnh báo đã xác nhận.</p>
          <div className="actions">
            <button type="button" className="button primary" disabled={working} onClick={() => { void decide("approve"); }}><Check size={19} />Duyệt cảnh báo</button>
            <button type="button" className="button secondary" disabled={working} onClick={() => { void decide("reject"); }}><X size={19} />Bác bỏ</button>
          </div>
        </div>}
      </section> : !error && <p role="status">Đang tải chiến dịch…</p> :
        <section className="panel workspace-panel">
          <div className="workspace-filters" role="group" aria-label="Trạng thái chiến dịch">{filters.map(filter =>
            <button type="button" key={filter} className={filter === state ? "filter active" : "filter"} aria-pressed={filter === state}
              onClick={() => setState(filter)}>{labels[filter]}</button>
          )}</div>
          {campaigns ? campaigns.length ? <ul className="campaign-list">{campaigns.map(item =>
            <li key={item.id}><Link href={"/ops/" + item.id} className="campaign">
              <span className="heading-icon"><Inbox size={21} /></span>
              <span><strong>{item.title}</strong><small>{formatDate(item.created)}</small></span>
              <span className={"badge risk-" + item.risk}>{riskLabels[item.risk]}</span>
            </Link></li>
          )}</ul> : <div className="empty"><Inbox size={30} /><p>Chưa có chiến dịch ở trạng thái này.</p></div> :
            !error && <p role="status" className="empty">Đang tải danh sách…</p>}
        </section>}
    </div>
  );
}
