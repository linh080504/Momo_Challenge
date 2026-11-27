import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { api, entityLabels, riskLabels, type OpsSample, type SampleLabel, type SampleReview } from "@/lib/api";

const labels: Record<SampleLabel, string> = {
  scam: "Lừa đảo", legit: "Hợp lệ", uncertain: "Cần xác minh", withdrawn: "Rút nhãn",
};
const channels: Record<string, string> = {
  text: "Tin nhắn", image: "Ảnh", url: "Website", qr: "QR", audio: "Ghi âm", receipt: "Biên lai",
};
type Page = { samples: OpsSample[]; next_cursor: string | null };

export function SampleReviewPanel({ campaignId, token, splitRevision }: {
  campaignId: string; token: string; splitRevision?: number;
}) {
  const router = useRouter();
  const [page, setPage] = useState<Page | null>(null);
  const [cursor, setCursor] = useState("");
  const [reload, setReload] = useState(0);
  const [saving, setSaving] = useState<string>();
  const [error, setError] = useState("");
  const endpoint = "/v1/ops/campaigns/" + encodeURIComponent(campaignId) + "/samples";

  useEffect(() => {
    const controller = new AbortController();
    api<Page>(endpoint + "?after=" + encodeURIComponent(cursor), "GET", undefined, token, controller.signal)
      .then(setPage).catch(failure => { if (!controller.signal.aborted) setError((failure as Error).message); });
    return () => controller.abort();
  }, [cursor, endpoint, reload, token]);

  async function review(event: FormEvent<HTMLFormElement>, sample: OpsSample) {
    event.preventDefault();
    if (saving) return;
    const label = new FormData(event.currentTarget).get("label");
    setSaving(sample.id);
    setError("");
    try {
      const saved = await api<SampleReview>(endpoint + "/" + encodeURIComponent(sample.id) + "/review", "POST",
        { label, revision: sample.history.at(-1)?.revision ?? 0 }, token);
      setPage(previous => previous && ({ ...previous, samples: previous.samples.map(item =>
        item.id === sample.id ? { ...item, history: [...item.history, saved] } : item) }));
    } catch (failure) {
      setError((failure as Error).message);
      setReload(value => value + 1);
    } finally {
      setSaving(undefined);
    }
  }

  return <details className="details">
    <summary>Gán nhãn báo cáo</summary>
    {error && <p role="alert" className="error">{error}</p>}
    {!page && !error && <p role="status">Đang tải báo cáo…</p>}
    {page?.samples.length === 0 && <p className="muted">Hồ sơ chưa có mẫu để gán nhãn.</p>}
    {page?.samples.map(sample => <div className="ops-sample" key={sample.id}>
      <h4>Mẫu {sample.id.slice(0, 8).toUpperCase()}</h4>
      <p>{riskLabels[sample.risk]} · {(sample.inputs ?? []).map(input => channels[input] ?? entityLabels[input] ?? input).join(", ") || "Kênh chưa ghi nhận"}</p>
      {sample.signals.length > 0 && <ul className="question-list">{sample.signals.map(signal => <li key={signal}>{signal}</li>)}</ul>}
      <form className="actions" onSubmit={event => { void review(event, sample); }} key={sample.history.at(-1)?.revision ?? 0}>
        <label>Nhãn
          <select name="label" defaultValue={sample.history.at(-1)?.label ?? ""} required>
            <option value="" disabled>Chọn nhãn</option>
            {Object.entries(labels).map(([key, text]) => <option key={key} value={key}>{text}</option>)}
          </select>
        </label>
        <button className="button secondary" disabled={Boolean(saving)}>Lưu nhãn</button>
      </form>
      {splitRevision !== undefined && <details>
        <summary>Tách báo cáo sang chiến dịch mới</summary>
        <button type="button" className="button secondary" disabled={Boolean(saving)} onClick={async () => {
          setSaving(sample.id);
          setError("");
          try {
            const split = await api<{ campaign_id: string }>(endpoint + "/" + encodeURIComponent(sample.id) + "/split",
              "POST", { revision: splitRevision }, token);
            router.push("/ops/" + encodeURIComponent(split.campaign_id));
          } catch (failure) {
            setError((failure as Error).message);
            setSaving(undefined);
          }
        }}>Xác nhận tách</button>
      </details>}
      {sample.history.length > 0 && <details>
        <summary>Lịch sử nhãn ({sample.history.length})</summary>
        <ul className="question-list">{sample.history.map(item => <li key={item.revision}>
          {labels[item.label]} · {item.actor} · {new Date(item.created * 1000).toLocaleString("vi-VN")}
        </li>)}</ul>
      </details>}
    </div>)}
    <div className="actions">
      {cursor && <button type="button" className="button secondary" disabled={Boolean(saving)}
        onClick={() => { setPage(null); setCursor(""); }}>Về trang đầu</button>}
      {page?.next_cursor && <button type="button" className="button secondary" disabled={Boolean(saving)}
        onClick={() => { const next = page.next_cursor; if (next) { setPage(null); setCursor(next); } }}>Trang tiếp</button>}
    </div>
  </details>;
}
