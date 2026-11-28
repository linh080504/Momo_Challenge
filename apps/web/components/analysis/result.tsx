"use client";

import { AlertTriangle, CircleHelp, Info, ShieldCheck } from "lucide-react";
import { entityLabels, riskLabels, type Analysis, type Session } from "@/lib/api";
import { ResultActions } from "./result-actions";
import { BrandNotice } from "./brand-notice";
import { ReceiptEvidence } from "./receipt-evidence";
import { WebsiteReportPanel, type WebsiteRefresh } from "./website-report";

const sources: Record<string, string> = {
  internal_blacklist: "Chiến dịch đã duyệt",
  external_blacklist: "Danh sách cảnh báo cộng đồng",
  domain_check: "Kiểm tra tên miền",
  safe_browsing: "Google Safe Browsing",
  rules: "Dấu hiệu theo quy tắc",
  llm: "Mô hình phân tích",
  vietqr: "Kiểm tra VietQR",
  document: "Phân tích biên lai",
  rdap: "Dữ liệu đăng ký tên miền",
  fraud_url_ml: "Mô hình nhận diện phishing",
  website_content: "Nội dung công khai của trang",
  url_reputation: "Đối chiếu danh sách nguy hiểm",
};

export function Result({ result, initialSession, receipt, websiteImage, websiteRefresh }: {
  result: Analysis; initialSession: Session | null; receipt?: File | null; websiteImage?: File | null; websiteRefresh?: WebsiteRefresh;
}) {
  const confirmed = result.evidence.some(item => item.source === "internal_blacklist" && item.weight > 0);
  const insufficientEvidence = result.risk_level === "uncertain" && result.risk_score === 0;
  const limitedWebsite = Boolean(result.website_report) && insufficientEvidence;
  const officialBrand = result.url_checks?.length === 1 ? result.url_checks[0].official_brand : null;
  const urlOnly = result.website_report && !result.website_report.screenshot && !result.website_report.markup &&
    !result.website_report.article && result.website_report.public_page?.status !== "read";
  const summary = limitedWebsite && urlOnly ? (officialBrand ?
    `Địa chỉ thuộc tên miền chính thức của ${officialBrand}. Nội dung cụ thể của trang chưa được kiểm tra.` :
    "Chưa thấy tín hiệu rủi ro trong dữ liệu đối chiếu. Nội dung cụ thể của trang chưa được kiểm tra.") : result.summary;

  const riskTitle = limitedWebsite && urlOnly ? "Cần xác minh nội dung trang" : riskLabels[result.risk_level];
  const banner = result.website_report ? <div className="website-assessment">
    <h2 className={`website-assessment-label risk-${result.risk_level}`}>{riskTitle}</h2>
    <p className="website-assessment-score">Điểm rủi ro <strong className={`risk-${result.risk_level}`}>
      {limitedWebsite ? "Chưa đủ dữ liệu" : `${result.risk_score}/100`}
    </strong></p>
    <p className="muted">{summary}</p>
  </div> : <div className={"result-banner risk-" + result.risk_level}>
        <span className="result-icon">{result.risk_level === "low" ? <ShieldCheck size={26} /> : <AlertTriangle size={26} />}</span>
        <div><h2>{riskTitle}</h2><p>{summary}</p></div>
        {!insufficientEvidence && <div className="result-score" aria-label={result.risk_score + " trên 100"}>{result.risk_score}<small>/100</small></div>}
      </div>;
  return (
    <section className={result.website_report ? "result-panel website-result-panel" : "panel result-panel"} aria-label="Kết quả phân tích">
      {result.brand_alert && <BrandNotice alert={result.brand_alert} />}
      {result.website_report ? <WebsiteReportPanel result={result} image={websiteImage} banner={banner} refresh={websiteRefresh} /> : banner}
      <div className="result-body">
        {confirmed && !result.brand_alert && <p className="notice verified"><ShieldCheck size={20} /> Cảnh báo đã được chuyên viên xác nhận.</p>}
        {result.degraded && !result.website_report && <p className="notice"><Info size={19} /> Chế độ hạn chế. Một phần dịch vụ đối chiếu hoặc mô hình đang tắt hoặc gián đoạn.</p>}
        {result.model === "qwen4-max" && (!result.website_report || result.image_reader === "qwen4-max") &&
          <p className="muted">Qwen4-Max đã đánh giá các dấu hiệu trích được từ nội dung.</p>}
        {result.image_reader === "qwen4-max" && <p className="muted">Ảnh được đọc bằng Qwen4-Max Vision.</p>}
        {result.image_reader === "local_ocr_fallback" &&
          <p className="notice"><Info size={19} /> Qwen chưa đọc được ảnh. Hệ thống đã dùng OCR cục bộ.</p>}
        {result.document && <ReceiptEvidence evidence={result.document} file={receipt} />}
        {!result.website_report && result.url_checks && <details className="details">
          <summary>Kiểm tra tên miền</summary>
          <ul className="evidence">{result.url_checks.map((item, index) => <li key={item.host + index}>
            <strong className="qr-host">{item.host}</strong>
            {item.domain_age_days !== null && <p>Đã đăng ký {item.domain_age_days} ngày trước</p>}
            {item.signals.map(signal => <p key={signal}>{signal}</p>)}
          </li>)}</ul>
        </details>}
        {!!result.content_context?.length && <>
          <h3>Ngữ cảnh của nội dung</h3>
          <ul className="flag-list">{result.content_context.map(item =>
            <li key={item.quote + item.reason}><blockquote>“{item.quote}”</blockquote><p>{item.reason}</p></li>)}</ul>
        </>}
        <h3>Dấu hiệu nhận thấy</h3>
        {result.red_flags.length ? <ul className="flag-list">{result.red_flags.map(flag =>
          <li key={flag.quote + flag.reason}><blockquote>“{flag.quote}”</blockquote><p>{flag.reason}</p></li>
        )}</ul> : <p className="muted">Chưa ghi nhận câu chữ chứa dấu hiệu rủi ro rõ ràng.</p>}
        <h3><CircleHelp size={19} /> Câu hỏi kiểm chứng</h3>
        <ul className="question-list">{result.verification_questions.map(question => <li key={question}>{question}</li>)}</ul>
        {!!result.guidance?.length && <details className="details">
          <summary>Hướng dẫn theo nhóm thủ đoạn</summary>
          <ul className="question-list">{result.guidance.map(item => <li key={item.id}>{item.text}
            {item.source_url && <a className="website-source-link" href={item.source_url} target="_blank"
              rel="noopener noreferrer">Xem hướng dẫn gốc</a>}
          </li>)}</ul>
        </details>}
        {(result.entities.length > 0 || result.evidence.length > 0) &&
          <details className="details">
            <summary>Xem bằng chứng và thông tin đã trích</summary>
            {result.entities.length > 0 && <div className="chips">{result.entities.map((entity, index) =>
              <span className="chip" key={index}>{entityLabels[entity.type] || entity.type} · {entity.display}</span>
            )}</div>}
            <ul className="evidence">{result.evidence.map((item, index) => <li key={item.source + index}>
              <strong>{sources[item.source] || item.source}</strong><p>{item.finding}</p>
            </li>)}</ul>
          </details>}
        <p className="disclaimer">{result.ai_disclaimer}</p>
        <ResultActions key={result.analysis_id} analysisId={result.analysis_id} initialSession={initialSession} />
      </div>
    </section>
  );
}
