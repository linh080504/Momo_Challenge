import { FileSearch, Globe2, ListChecks, RotateCw, ScanEye, Sparkles } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { type Analysis, type WebsiteReport } from "@/lib/api";
import { WebsiteSnapshot } from "./website-snapshot";
import { brandLabels } from "./brand-notice";

export type WebsiteRefresh = {
  busy: boolean;
  picture?: string;
  error: string;
  run: () => void;
};

const sources = [
  ["domain", "Bộ kiểm tra tên miền"],
  ["community", "Danh sách cộng đồng"],
  ["approved_cases", "Hồ sơ đã duyệt"],
  ["safe_browsing", "Google Safe Browsing"],
  ["rdap", "Đăng ký tên miền (RDAP)"],
] as const;
const reputationSources = [["virustotal", "VirusTotal"], ["urlhaus", "URLhaus"], ["phishtank", "PhishTank"]] as const;

const labels: Record<WebsiteReport["sources"][keyof WebsiteReport["sources"]], string> = {
  match: "Có tín hiệu",
  clear: "Chưa thấy trùng",
  checked: "Đã đối chiếu",
  unavailable: "Chưa có kết quả",
};
const pageStatus = {
  restricted: "Địa chỉ nằm ngoài phạm vi kiểm tra nội dung công khai.",
  redirect: "Trang chuyển hướng ra ngoài tên miền hoặc vượt giới hạn chuyển hướng.",
  unsupported: "Định dạng phản hồi của trang chưa được hỗ trợ.",
  unavailable: "Chưa đọc được nội dung công khai của trang.",
  too_large: "Nội dung trang vượt giới hạn xử lý của PayPause.",
  busy: "Đang có nhiều lượt đọc website. Hãy thử lại sau.",
};

export function WebsiteReportPanel({ result, image, banner, refresh }: {
  result: Analysis; image?: File | null; banner: ReactNode; refresh?: WebsiteRefresh;
}) {
  const report = result.website_report;
  const domains = result.url_checks ?? [];
  const [preview, setPreview] = useState<string | null>(null);
  useEffect(() => {
    if (!image) return;
    const objectUrl = URL.createObjectURL(image);
    // Synchronize the preview with the browser-managed object URL.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPreview(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [image]);
  if (!report || !domains.length) return null;
  const article = report.article;
  const page = report.public_page;
  const capture = article?.capture_jpeg || page?.capture_jpeg;
  const picture = capture ? `data:image/jpeg;base64,${capture}` :
    article?.image_webp ? `data:image/webp;base64,${article.image_webp}` : preview;
  const pictureLabel = article?.image_webp ? `Ảnh minh họa từ ${article.publisher}` : "Ảnh người dùng gửi";
  const host = article?.host ?? domains[0].host;
  const checkedAt = page?.checked_at === undefined ? null : new Date(page.checked_at * 1000);
  const notes = page?.explanation ?? [];
  const articleNotes = notes.filter(reason => reason.kind === "article");
  const riskNotes = notes.filter(reason => reason.kind !== "article");
  return <section className="website-report" aria-label="Báo cáo kiểm tra website">
    <section className="website-report-block website-verdict">
      <h3><Sparkles size={21} aria-hidden="true" /> {result.model === "qwen4-max" ? "Kết quả phân tích của PayPause AI" : "Kết quả kiểm tra website"}</h3>
      {refresh?.busy && <p className="muted" role="status">Đang phân tích lại. Bên dưới là kết quả lần trước.</p>}
      {banner}
      {report.brand_review && <details className="details" open={report.brand_review.verdict === "IMPOSTOR" || undefined}>
        <summary>Kiểm tra mạo danh · {brandLabels[report.brand_review.verdict]}</summary>
        {report.brand_review.source === "submitted_html" && <p className="muted">Dựa trên HTML đính kèm.</p>}
        <ul className="question-list">{report.brand_review.findings.map(finding => <li key={finding}>{finding}</li>)}</ul>
      </details>}
      {notes.length ? <div className="website-explanation">
        {articleNotes.length > 0 && <section aria-labelledby="website-article-title">
          <h4 id="website-article-title">AI phân tích nội dung trang</h4>
          {page?.title && <p className="muted">{page.title}</p>}
          <ul>{articleNotes.map(reason => <li key={reason.label}>
            <p>{reason.finding}</p>
            {reason.support && <details className="website-excerpt">
              <summary>Xem đoạn trích làm căn cứ</summary>
              <blockquote>{reason.support}</blockquote>
            </details>}
          </li>)}</ul>
        </section>}
        {riskNotes.length > 0 && <section aria-labelledby="website-explanation-title">
        <h4 id="website-explanation-title">Dấu hiệu và căn cứ đánh giá rủi ro</h4>
        <ul>{riskNotes.map(reason => <li key={reason.label}>
          <p><strong>{reason.label}.</strong> {reason.finding}</p>
          {reason.support && <details className="website-excerpt">
            <summary>Đoạn trích dùng để phân tích</summary>
            <blockquote>{reason.support}</blockquote>
          </details>}
          {reason.source_url && <a className="website-source-link" href={reason.source_url}
            target="_blank" rel="noopener noreferrer">Xem nguồn đối chiếu</a>}
        </li>)}</ul>
        </section>}
      </div> : page?.status === "read" && <p className="muted">{page.model
        ? "Qwen4-Max đã đánh giá mức rủi ro. Chi tiết bằng chứng nằm bên dưới."
        : "Qwen4-Max chưa trả kết quả. Phần dưới hiển thị các dấu hiệu đã tìm thấy và nguồn đối chiếu."}</p>}
      {article && !articleNotes.length && <article className="website-capture">
      <div className="website-article-content">
        <h4>{article.title}</h4>
        {article.context === "educational" && <p className="website-article-context">Qwen4-Max nhận diện nội dung hướng dẫn phòng tránh lừa đảo.</p>}
        {article.findings.length > 0 && <ul className="question-list">{article.findings.map(finding => <li key={finding}>{finding}</li>)}</ul>}
      </div>
    </article>}
      {(refresh || checkedAt) && <div className="website-refresh">
        {checkedAt && <p className="muted website-checked-at">Cập nhật <time dateTime={checkedAt.toISOString()}>
          {checkedAt.toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" })}
        </time></p>}
        {refresh?.error && <p role="alert" className="error">{refresh.error}</p>}
        {refresh && <button type="button" className="button secondary" onClick={refresh.run} disabled={refresh.busy}>
          <RotateCw size={17} aria-hidden="true" /> Phân tích lại
        </button>}
      </div>}
      <h3><Globe2 size={19} aria-hidden="true" /> Phát hiện trên đường link</h3>
      <ul className="evidence">{domains.map((domain, index) => <li key={`${domain.host}-${index}`}>
        <strong className="qr-host">{domain.host}</strong>
        {domain.domain_registered_on ? <p>Ngày đăng ký theo RDAP <time dateTime={domain.domain_registered_on}>
          {domain.domain_registered_on.split("-").reverse().join("/")}</time></p> :
          domain.domain_age_days !== null && <p>Đăng ký {domain.domain_age_days} ngày trước</p>}
        {domain.signals.length ? <ul className="question-list">{domain.signals.map((signal, signalIndex) =>
          <li key={signalIndex}>{signal}</li>)}</ul> : <p>Chưa thấy dấu hiệu bất thường trong cấu trúc địa chỉ.</p>}
      </li>)}</ul>
      {page?.status === "read" && !notes.length && <div className="website-capture">
        <h3><FileSearch size={19} aria-hidden="true" /> Phát hiện từ nội dung trang</h3>
        {!!page.findings?.length ? <ul className="question-list">{page.findings.map(finding => <li key={finding}>{finding}</li>)}</ul> :
          <p className="muted">Phần trang đã đọc chưa cung cấp đủ dấu hiệu để kết luận.</p>}
      </div>}
      {report.screenshot && <div className="website-capture">
        <h3><FileSearch size={18} aria-hidden="true" /> Nội dung ảnh giao diện</h3>
        {report.screenshot.credential_labels.length ?
          <p>Ảnh có chữ liên quan đến {report.screenshot.credential_labels.join(", ")}. Hãy xác minh nguồn trước khi nhập thông tin.</p> :
          <p>OCR chưa thấy nhãn mật khẩu, mã xác thực hoặc thẻ ngân hàng trong ảnh.</p>}
        {!!report.screenshot?.brands?.length && <ul className="question-list">{report.screenshot.brands.map(brand =>
          <li key={brand.name}>Ảnh nhắc đến {brand.name}. {brand.domain_matches ?
            "Tên miền đầu tiên khớp danh mục thương hiệu." : "Tên miền đầu tiên chưa khớp danh mục thương hiệu."}</li>)}</ul>}
      </div>}
      {report.markup && <div className="website-capture">
        <h3><FileSearch size={18} aria-hidden="true" /> Mã nguồn được gửi</h3>
        {report.markup.findings.length > 0 ? <ul className="question-list">{report.markup.findings.map(finding =>
          <li key={finding}>{finding}</li>)}</ul> :
          <p>{report.markup.status === "unreadable" ? "Chưa đọc được nội dung đã gửi." : "Chưa thấy dấu hiệu trong nội dung đã gửi."}</p>}
      </div>}
    </section>
    <div className="website-side">
    <section className="website-report-block website-visual">
      <h3><ScanEye size={21} aria-hidden="true" /> Hình ảnh website</h3>
      {refresh?.busy ? <WebsiteSnapshot picture={refresh.picture} host={host} /> :
       capture && picture ? <WebsiteSnapshot picture={picture} host={host} /> :
       picture ? <figure className="website-article-image">
        <img src={picture} alt={pictureLabel} />
        <figcaption className="muted">{pictureLabel}{article ? ` · ${article.host}` : ""}</figcaption>
      </figure> : page?.status === "read" ? <div className="website-visual-empty">
        <FileSearch size={30} aria-hidden="true" />
        <strong>{domains[0].host}</strong>
        {page.title && <h4>{page.title}</h4>}
        <p>{page.title === null ? "Ảnh của trang được ẩn." : "Đã đọc nội dung trang. Chưa chụp được ảnh trong lần kiểm tra này."}</p>
      </div> : <div className="website-visual-empty"><ScanEye size={30} aria-hidden="true" />
        <div>
          <strong>Chưa có ảnh trang</strong>
          <p>{page ? pageStatus[page.status] : report.capture_scope === "unlisted" ? "Báo cáo này chỉ dùng dữ liệu đối chiếu tên miền và bằng chứng đã gửi." :
            "Bạn có thể đính kèm ảnh có sẵn trong mục bằng chứng."}</p>
        </div>
      </div>}
    </section>
    <div className="website-report-block">
      <h3><ListChecks size={19} aria-hidden="true" /> Báo cáo theo nguồn</h3>
      {result.analysis_path === "deep" && <p className="notice">
        {page?.model ? "Qwen4-Max đã phân tích nội dung trang và các dấu hiệu thu được." :
          report.article?.model ? "Qwen4-Max đã đánh giá ngữ cảnh dựa trên các đề mục của bài viết." :
          result.model === "qwen4-max" ? "Qwen4-Max đã tổng hợp các tín hiệu rủi ro." : "Backend dùng tín hiệu hiện có khi Qwen chưa trả kết quả."}
      </p>}
      {result.analysis_path === "fast" && <p className="muted">Fast Path · Đối chiếu bằng luật và danh mục.</p>}
      <dl className="website-sources">{sources.map(([id, label]) => {
        const status = report.sources[id];
        return <div key={id}>
          <dt>{label}</dt>
          <dd className={`website-status website-status-${status}`}>
            {status === "unavailable" && (id === "safe_browsing" || id === "rdap") ? report.source_limits?.[id] ?? labels[status] :
              id === "domain" && status === "clear" ? "Chưa thấy bất thường" : labels[status]}
          </dd>
        </div>;
      })}
      {reputationSources.map(([id, name]) => {
        const source = report.reputation?.[id];
        if (!source) return null;
        return <div key={id}>
          <dt>{name}<small className="muted">{source.scope}</small></dt>
          <dd className={`website-status website-status-${source.status}`}>{labels[source.status]}</dd>
        </div>;
      })}</dl>
      <p className="muted">Hồ sơ đã duyệt đối chiếu thông tin trích từ nội dung bạn gửi. Safe Browsing đối chiếu ở cấp tên miền.</p>
    </div>
    </div>
  </section>;
}
