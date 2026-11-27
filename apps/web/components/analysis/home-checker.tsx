"use client";

import { useRouter } from "next/navigation";
import { saveCheckDraft, type CheckDraft } from "@/lib/check-draft";
import { CheckTabs } from "./check-tabs";

export function HomeChecker() {
  const router = useRouter();

  function submitCheck(draft: CheckDraft) {
    saveCheckDraft(draft);
    router.push("/website");
  }

  return <section id="kiem-tra" className="home-checker" aria-labelledby="check-heading">
    <CheckTabs onCheck={submitCheck} />
  </section>;
}
