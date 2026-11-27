"use client";

import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { takeCheckDraft, type CheckDraft } from "@/lib/check-draft";
import { CheckTabs } from "./check-tabs";

export function WebsiteWorkspace() {
  const [draft, setDraft] = useState<CheckDraft>();

  useEffect(() => {
    const next = takeCheckDraft();
    // Read the submitted fields once from the current browser tab.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (next) setDraft(next);
  }, []);

  return <div className="shell website-page">
    <div className="website-intro">
      <span className="heading-icon"><ShieldCheck size={26} aria-hidden="true" /></span>
      <h1>Kiểm tra nội dung đáng ngờ</h1>
      <p>Chọn loại nội dung bạn muốn kiểm tra trước khi chuyển tiền.</p>
    </div>
    <CheckTabs key={draft ? "submitted" : "ready"} initialDraft={draft} />
  </div>;
}
