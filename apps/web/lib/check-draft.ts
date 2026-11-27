export type AnalyzerKind = "website" | "text" | "image" | "receipt" | "audio";

export type AnalyzerDraft = {
  kind: AnalyzerKind;
  text: string;
  markup: string;
  file: File | null;
};

export type QrDraft = {
  kind: "qr";
  text: string;
  payload: string;
  file: File | null;
};

export type CheckDraft = AnalyzerDraft | QrDraft;

let pending: CheckDraft | undefined;

export function saveCheckDraft(draft: CheckDraft) {
  pending = draft;
}

export function takeCheckDraft() {
  const draft = pending;
  pending = undefined;
  return draft;
}
