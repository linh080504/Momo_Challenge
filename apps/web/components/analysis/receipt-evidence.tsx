"use client";

import { useEffect, useState } from "react";
import type { DocumentEvidence } from "@/lib/api";

export function ReceiptEvidence({ evidence, file }: { evidence: DocumentEvidence; file?: File | null }) {
  const [photo, setPhoto] = useState<string | null>(null);
  const [layer, setLayer] = useState<"ocr" | "compression">("ocr");

  useEffect(() => {
    if (!file) return;
    const localUrl = URL.createObjectURL(file);
    // Keep the original blob URL for the evidence overlay and revoke it on cleanup.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPhoto(localUrl);
    return () => URL.revokeObjectURL(localUrl);
  }, [file]);

  const regions = layer === "ocr" ? evidence.ocr_boxes : evidence.recompression_regions;
  return <details className="details" open>
    <summary>Đối chiếu ảnh biên lai</summary>
    {photo && <>
      <div className="actions" role="group" aria-label="Lớp đánh dấu trên biên lai">
        <button type="button" className="filter" aria-pressed={layer === "ocr"} onClick={() => setLayer("ocr")}>Vùng chữ OCR</button>
        <button type="button" className="filter" aria-pressed={layer === "compression"}
          onClick={() => setLayer("compression")}>Sai khác nén JPEG</button>
      </div>
      <figure className="receipt-preview">
        {/* The browser shows the original file, including its orientation. */}
        <img src={photo} alt="Ảnh biên lai gốc đã tải lên" />
        {regions.map(([x, y, width, height], index) => <span aria-hidden="true" key={index}
          className={layer === "ocr" ? "ocr-box" : "compression-box"}
          style={{ left: `${100 * x}%`, top: `${100 * y}%`, width: `${100 * width}%`, height: `${100 * height}%` }} />)}
      </figure>
      <p className="micro muted">{regions.length ? `${regions.length} vùng được đánh dấu` : "Chưa có vùng được đánh dấu ở lớp này."}</p>
    </>}
    <ul className="evidence">{evidence.signals.map(item => <li key={item.finding}>{item.finding}</li>)}</ul>
    <p className="notice">{evidence.notice}</p>
  </details>;
}
