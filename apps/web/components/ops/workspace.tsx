"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { Check, Inbox, LayoutGrid, RefreshCw, X } from "lucide-react";
import { LoginForm } from "@/components/login-form";
import { InvestigationWorkspace } from "./investigation";
import { SampleReviewPanel } from "./sample-review";
import {
  api, ApiError, currentSession, entityLabels, riskLabels, saveSession,
  type Campaign, type CampaignState, type OpsOverview, type OpsSystem, type Session,
} from "@/lib/api";

const labels: Record<CampaignState, string> = { pending: "Chờ duyệt", approved: "Đã duyệt", rejected: "Đã bác bỏ" };
const groups = {
  G1: "Mạo danh cơ quan, tổ chức", G2: "Mạo danh người quen", G3: "Đầu tư hoặc tuyển dụng",
  G4: "Mua bán và giao dịch trực tuyến", G5: "Đánh cắp dữ liệu hoặc tài khoản",
};
const historyLabels = { approve: "Duyệt", reject: "Bác bỏ", edit_group: "Cập nhật phân loại", split_sample: "Tách báo cáo" };
const filters: CampaignState[] = ["pending", "approved", "rejected"];
const formatDate = (seconds: number) => new Date(seconds * 1000).toLocaleString("vi-VN");
const channelLabels = { web: "Website", in_app: "Trong ứng dụng", email: "Email", sms: "SMS", internal: "Nội bộ" };

export function Workspace({ campaignId }: { campaignId?: string }) {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [state, setState] = useState<CampaignState>("pending");
  const [campaigns, setCampaigns] = useState<Campaign[] | null>(null);
  const [detail, setDetail] = useState<Campaign | null>(null);
  const [overview, setOverview] = useState<OpsOverview | null>(null);
  const [system, setSystem] = useState<OpsSystem | null>(null);
  const [systemError, setSystemError] = useState(false);
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
      : Promise.all([
        api<Campaign[]>("/v1/ops/campaigns?state=" + state, ...options),
        api<OpsOverview>("/v1/ops/overview", ...options),
      ]).then(([items, metrics]) => { setCampaigns(items); setOverview(metrics); });
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

  useEffect(() => {
    if (campaignId || session?.role !== "ops") return;
    const controller = new AbortController();
    api<OpsSystem>("/v1/ops/system", "GET", undefined, session.token, controller.signal)
      .then(data => { setSystem(data); setSystemError(false); })
      .catch(() => { if (!controller.signal.aborted) setSystemError(true); });
    return () => controller.abort();
  }, [campaignId, reload, session]);

  async function decide(decision: "approve" | "reject") {
    if (!session || !detail || working) return;
    setWorking(true);
    setError("");
    try {
      const updated = await api<Campaign>("/v1/ops/campaigns/" + detail.id + "/decision", "POST",
        { decision, revision: detail.revision }, session.token);
      setDetail({ ...detail, ...updated });
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
        {detail.alerts && <details className="details">
          <summary>Cảnh báo theo kênh</summary>
          <p className="muted">Đối chiếu trạng thái giao dịch qua ngân hàng. Hồ sơ hiện chưa có kết quả xác minh giao dịch.</p>
          <ul className="question-list">{detail.alerts.channels.map(channel => <li key={channel.id}>
            <strong>{channelLabels[channel.id]} · {channel.state === "published" ? "Đã bật cảnh báo khi kiểm tra trùng" : "Bản xem trước"}</strong>
            <p>{channel.title}</p><p>{channel.body}</p>
          </li>)}</ul>
        </details>}
        <SampleReviewPanel campaignId={detail.id} token={session.token}
          splitRevision={detail.state === "pending" && detail.report_count > 1 ? detail.revision : undefined} />
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
          <details className="details ops-system">
            <summary>Cấu hình hệ thống</summary>
            {systemError ? <p role="alert">Chưa đọc được cấu hình. Hãy tải lại.</p> : system ? <>
              <p className="muted">API {system.app_version} · Prompt {system.prompt_version} · Tri thức {system.knowledge_version}</p>
              <dl className="website-sources">{[
                ["Qwen", system.qwen_model],
                ["Đọc nội dung website", system.website_read_enabled],
                ["Ảnh chụp website", system.website_read_enabled && system.website_capture_enabled],
                ["Phiên âm Whisper", system.speech_configured],
                ["Google Safe Browsing", system.safe_browsing_configured],
                ["VirusTotal", system.reputation_configured.virustotal],
                ["URLhaus", system.reputation_configured.urlhaus],
                ["PhishTank", system.reputation_configured.phishtank],
                ["RDAP", system.reputation_configured.rdap],
              ].map(([label, enabled]) => <div key={String(label)}>
                <dt>{label}</dt><dd>{typeof enabled === "string" ? enabled : enabled ? "Đã cấu hình" : "Chưa cấu hình"}</dd>
              </div>)}</dl>
            </> : <p role="status">Đang tải cấu hình…</p>}
          </details>
          {overview && <dl className="ops-overview" aria-label="Tổng quan vận hành">
            <div><dt>Báo cáo trong 24 giờ</dt><dd>{overview.reports_24h}</dd></div>
            <div><dt>Quyết định trong 24 giờ</dt><dd>{overview.decisions_24h}</dd></div>
            <div><dt>Chiến dịch chờ duyệt</dt><dd>{overview.pending}</dd></div>
            <div><dt>Chiến dịch đã duyệt</dt><dd>{overview.approved}</dd></div>
          </dl>}
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
