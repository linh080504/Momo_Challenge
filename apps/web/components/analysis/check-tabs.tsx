"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Globe2, Image, MessageSquare, Mic, ReceiptText, ScanLine, Search } from "lucide-react";
import { type CheckDraft } from "@/lib/check-draft";
import { AnalyzerForm } from "./analyzer-form";
import { QrChecker } from "./qr-checker";

const options = [
  { kind: "website", label: "Website", icon: Globe2 },
  { kind: "text", label: "Tin nhắn", icon: MessageSquare },
  { kind: "image", label: "Ảnh chụp", icon: Image },
  { kind: "qr", label: "Mã QR", icon: ScanLine },
  { kind: "receipt", label: "Biên lai", icon: ReceiptText },
  { kind: "audio", label: "Ghi âm", icon: Mic },
] as const;

export function CheckTabs({ initialDraft, onCheck }: {
  initialDraft?: CheckDraft;
  onCheck?: (draft: CheckDraft) => void;
}) {
  const compact = onCheck !== undefined;
  const [active, setActive] = useState(initialDraft ? options.findIndex(({ kind }) => kind === initialDraft.kind) : 0);
  const tabs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    function selectLinkedTab() {
      const index = options.findIndex(({ kind }) => window.location.hash === `#kiem-tra-${kind}`);
      if (index >= 0) setActive(index);
    }
    selectLinkedTab();
    window.addEventListener("hashchange", selectLinkedTab);
    return () => window.removeEventListener("hashchange", selectLinkedTab);
  }, []);

  function selectTab(index: number) {
    setActive(index);
    if (window.location.hash.startsWith("#kiem-tra-")) {
      window.history.replaceState(null, "", `#kiem-tra-${options[index].kind}`);
    }
  }

  function navigate(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next: number;
    if (event.key === "Home") next = 0;
    else if (event.key === "End") next = options.length - 1;
    else if (event.key === "ArrowRight") next = (index + 1) % options.length;
    else if (event.key === "ArrowLeft") next = (index + options.length - 1) % options.length;
    else return;
    event.preventDefault();
    selectTab(next);
    tabs.current[next]?.focus();
  }

  return <>
    <div className={compact ? "home-checker-header" : undefined}>
      {compact && <h2 id="check-heading"><Search size={22} aria-hidden="true" /> Kiểm tra ngay</h2>}
      <div className="check-tabs" role="tablist" aria-label="Loại nội dung cần kiểm tra">
        {options.map(({ kind, label, icon: Icon }, index) => (
          <button key={kind} ref={button => { tabs.current[index] = button; }} type="button" role="tab"
            id={`kiem-tra-${kind}`} aria-controls={`check-panel-${kind}`} aria-selected={active === index}
            tabIndex={active === index ? 0 : -1} onClick={() => selectTab(index)}
            onKeyDown={event => navigate(event, index)}>
            <Icon size={17} aria-hidden="true" /> {label}
          </button>
        ))}
      </div>
    </div>
    {options.map(({ kind }, index) => (
      <div key={kind} id={`check-panel-${kind}`} role="tabpanel"
        aria-labelledby={`kiem-tra-${kind}`} hidden={active !== index}>
        {kind === "qr" ? <div className={compact ? "panel input-panel" : "form-column"}>
          <QrChecker embedded={compact} headingLevel="h2"
            initialDraft={initialDraft?.kind === "qr" ? initialDraft : undefined} onCheck={onCheck} />
        </div> : <AnalyzerForm kind={kind} compact={compact}
          initialDraft={initialDraft?.kind === kind ? initialDraft : undefined} onCheck={onCheck} />}
      </div>
    ))}
  </>;
}
