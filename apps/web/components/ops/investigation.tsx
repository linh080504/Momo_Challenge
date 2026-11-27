"use client";

import Link from "next/link";
import { useState } from "react";
import { riskLabels, type AgentReview, type Investigation, type OpsWorkspace } from "@/lib/api";

function CampaignGraph({ graph }: { graph: Investigation }) {
  const [selected, setSelected] = useState("campaign");
  const ring = graph.nodes.filter(node => node.id !== "campaign");
  const positions = new Map([["campaign", { x: 50, y: 50 }], ...ring.map((node, index) => {
    const angle = (2 * Math.PI * index) / ring.length - Math.PI / 2;
    return [node.id, { x: 50 + 37 * Math.cos(angle), y: 50 + 37 * Math.sin(angle) }] as const;
  })]);
  const activeNode = graph.nodes.find(node => node.id === selected) || graph.nodes[0];
  const adjacent = graph.edges.filter(edge => edge.from === activeNode.id || edge.to === activeNode.id);

  return <div className="investigation-graph">
    <div className="graph-map" role="group" aria-label="Bản đồ thực thể trong chiến dịch">
      {graph.edges.map(edge => {
        const from = positions.get(edge.from);
        const to = positions.get(edge.to);
        if (!from || !to) return null;
        const x = to.x - from.x;
        const y = to.y - from.y;
        const active = adjacent.includes(edge);
        return <span aria-hidden="true" key={edge.from + edge.to} className={`graph-line${active ? " active" : ""}`}
          style={{ left: `${from.x}%`, top: `${from.y}%`, width: `${Math.hypot(x, y)}%`, transform: `rotate(${Math.atan2(y, x)}rad)` }} />;
      })}
      {graph.nodes.map(node => {
        const point = positions.get(node.id)!;
        return <button type="button" className="graph-node" key={node.id} aria-pressed={node.id === activeNode.id}
          style={{ left: `${point.x}%`, top: `${point.y}%` }} onClick={() => setSelected(node.id)}>
          <span>{node.label}</span>{node.count !== null && <strong>{node.count}</strong>}
        </button>;
      })}
    </div>
    <div className="graph-details" aria-live="polite">
      <strong>{activeNode.label}</strong>
      <ul>{adjacent.map(edge => {
        const neighbor = graph.nodes.find(node => node.id === (edge.from === activeNode.id ? edge.to : edge.from));
        return <li key={edge.from + edge.to}>
          {neighbor?.label} · {edge.count}
          {edge.source === "report_cooccurrence" && " báo cáo có cả hai tín hiệu"}
          {edge.last_seen && <> · Gần nhất {new Date(edge.last_seen * 1000).toLocaleString("vi-VN")}</>}
        </li>;
      })}</ul>
    </div>
  </div>;
}

const mediaLabels: Record<string, string> = { receipt: "biên lai", image: "ảnh", audio: "bản ghi âm" };

const reviewStatus = {
  ok: "",
  disabled: "Qwen chưa được cấu hình.",
  quota: "Đã hết lượt gọi Qwen hôm nay.",
  unavailable: "Chưa nhận được phản hồi từ Qwen.",
  invalid: "Phản hồi Qwen chưa hợp lệ.",
};

function ReviewNote({ review }: { review?: AgentReview }) {
  if (!review) return null;
  return review.status === "ok" ? <p className="notice"><strong>Qwen</strong> {review.note}</p> :
    <p className="micro muted">{reviewStatus[review.status]}</p>;
}

export function InvestigationWorkspace({ workspace }: { workspace: OpsWorkspace }) {
  return <section className="investigation-workspace" aria-labelledby="investigation-workspace-title">
    <h3 id="investigation-workspace-title">Bàn điều tra đa tác nhân</h3>
    <p className="muted">Supervisor cấp quyền đọc bằng chứng và soạn bản nháp. Chuyên viên duyệt cảnh báo.</p>
    <ReviewNote review={workspace.supervisor_review} />
    <details className="details" open>
      <summary>Investigation · Bản đồ chiến dịch</summary>
      <ReviewNote review={workspace.investigation.review} />
      <CampaignGraph graph={workspace.investigation} />
      {workspace.investigation.related_campaigns.length > 0 && <ul className="question-list">
        {workspace.investigation.related_campaigns.map(item => <li key={item.id}>
          <Link href={`/ops/${item.id}`}>{item.id.slice(0, 8).toUpperCase()}</Link>
          {` · ${item.shared_entities} thực thể trùng · ${item.state === "approved" ? "Đã duyệt" : "Chờ duyệt"}`}
        </li>)}
      </ul>}
    </details>
    <details className="details">
      <summary>Detection · Tín hiệu rủi ro</summary>
      <ReviewNote review={workspace.detection.review} />
      <p>{riskLabels[workspace.detection.risk]}</p>
      <ul className="question-list">{workspace.detection.signals.map(signal => <li key={signal}>{signal}</li>)}</ul>
    </details>
    <details className="details">
      <summary>Threat Intel · Chiến dịch đã xác minh</summary>
      <ReviewNote review={workspace.threat_intel.review} />
      {workspace.threat_intel.confirmed_related_campaigns.length ? <ul className="question-list">
        {workspace.threat_intel.confirmed_related_campaigns.map(id => <li key={id}>
          <Link href={`/ops/${id}`}>{id.slice(0, 8).toUpperCase()}</Link>
        </li>)}
      </ul> : <p className="muted">Chưa có chiến dịch đã duyệt trùng thực thể.</p>}
      {workspace.threat_intel.safe_browsing_hits > 0 && <p>{workspace.threat_intel.safe_browsing_hits} báo cáo có tên miền trùng Safe Browsing.</p>}
    </details>
    <details className="details">
      <summary>Forensics · Ảnh và ghi âm</summary>
      <ReviewNote review={workspace.forensics.review} />
      <p>{Object.entries(workspace.forensics.reviewed_input_counts).map(([kind, count]) => `${count} ${mediaLabels[kind]}`).join(" · ")
        || "Chưa có tệp ảnh hoặc ghi âm trong các báo cáo của chiến dịch."}</p>
      {workspace.forensics.reviewed_input_counts.receipt > 0 && <p>
        {workspace.forensics.ocr_regions} vùng OCR · {workspace.forensics.jpeg_regions} vùng sai khác nén · Giao dịch cần xác minh
      </p>}
    </details>
    <details className="details">
      <summary>Protection · Đề xuất bảo vệ người dùng</summary>
      <ReviewNote review={workspace.protection.review} />
      <ul className="question-list">{workspace.protection.recommendations.map(item => <li key={item}>{item}</li>)}</ul>
    </details>
    <details className="details">
      <summary>Report · Bản nháp chờ duyệt</summary>
      <ReviewNote review={workspace.report.review} />
      <h4>{workspace.report.title}</h4><p>{workspace.report.summary}</p><p>{workspace.report.recommendation}</p>
    </details>
  </section>;
}
