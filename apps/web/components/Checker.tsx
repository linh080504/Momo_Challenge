"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnalyzeError, analyze } from "@/lib/api";
import { ImageError, prepareImage, type PreparedImage } from "@/lib/image";
import { SAMPLES, type Sample } from "@/lib/samples";
import type { Analysis } from "@/lib/types";
import ErrorPanel from "./ErrorPanel";
import InputPanel from "./InputPanel";
import ProgressScreen, { INITIAL_PROGRESS, applyProgress, type ProgressState } from "./ProgressScreen";
import ResultCard from "./ResultCard";

type View = "input" | "working" | "result" | "error";

export default function Checker() {
  const [view, setView] = useState<View>("input");

  // Đầu vào: giữ nguyên khi hủy hoặc lỗi để người dùng không phải nhập lại.
  const [text, setText] = useState("");
  const [image, setImage] = useState<PreparedImage | null>(null);
  const [imageBusy, setImageBusy] = useState(false);
  const [imageError, setImageError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // "Dùng mẫu": chỉ điền ĐẦU VÀO. Kết quả luôn do API thật trả về.
  const [nextSample, setNextSample] = useState(0);
  const [activeSample, setActiveSample] = useState<Sample | null>(null);

  const [progress, setProgress] = useState<ProgressState>(INITIAL_PROGRESS);
  const [result, setResult] = useState<Analysis | null>(null);
  const [error, setError] = useState<AnalyzeError | null>(null);

  const headingRef = useRef<HTMLHeadingElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const imageRef = useRef<PreparedImage | null>(null);
  const previousView = useRef<View>(view);

  // Chuyển màn hình thì đưa tiêu đề lên đầu và trỏ focus vào đó (trình đọc màn hình đọc đúng chỗ).
  useEffect(() => {
    if (previousView.current === view) return;
    previousView.current = view;
    window.scrollTo({ top: 0 });
    headingRef.current?.focus({ preventScroll: true });
  }, [view]);

  // Rời trang: dừng yêu cầu đang chạy và giải phóng ảnh xem trước.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      if (imageRef.current) URL.revokeObjectURL(imageRef.current.previewUrl);
    };
  }, []);

  const replaceImage = useCallback((next: PreparedImage | null) => {
    if (imageRef.current) URL.revokeObjectURL(imageRef.current.previewUrl);
    imageRef.current = next;
    setImage(next);
  }, []);

  const handlePickFile = useCallback(
    async (file: File) => {
      setImageError(null);
      setImageBusy(true);
      try {
        const prepared = await prepareImage(file);
        replaceImage(prepared);
        setFormError(null);
        setActiveSample(null);
      } catch (e) {
        setImageError(e instanceof ImageError ? e.message : "Không đọc được ảnh này. Hãy thử ảnh khác.");
      } finally {
        setImageBusy(false);
      }
    },
    [replaceImage],
  );

  function handleUseSample() {
    const sample = SAMPLES[nextSample % SAMPLES.length];
    setText(sample.text);
    replaceImage(null);
    setImageError(null);
    setFormError(null);
    setActiveSample(sample);
    setNextSample((n) => n + 1);
  }

  function handleTextChange(value: string) {
    setText(value);
    setActiveSample(null); // đã tự sửa thì không còn là "mẫu" nữa
    setFormError(null);
  }

  async function handleSubmit() {
    const trimmed = text.trim();
    if (!trimmed && !image) {
      setFormError("Hãy dán tin nhắn hoặc chọn ảnh trước khi bấm Kiểm tra.");
      textareaRef.current?.focus();
      return;
    }

    setFormError(null);
    setError(null);
    setResult(null);
    setProgress(INITIAL_PROGRESS);
    setView("working");

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const data = await analyze(
        { text: trimmed, image: image ? { base64: image.base64, mime: image.mime } : undefined },
        {
          signal: controller.signal,
          onProgress: (event) => {
            if (abortRef.current === controller) setProgress((prev) => applyProgress(prev, event));
          },
        },
      );
      if (abortRef.current !== controller) return; // đã hủy hoặc đã gửi lần khác
      setResult(data);
      setView("result");
    } catch (e) {
      if (abortRef.current !== controller) return;
      if (e instanceof AnalyzeError && e.kind === "aborted") return;
      setError(
        e instanceof AnalyzeError
          ? e
          : new AnalyzeError("network", "Có lỗi không mong muốn. Hãy thử lại."),
      );
      setView("error");
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
    }
  }

  function handleCancel() {
    abortRef.current?.abort();
    abortRef.current = null;
    setView("input"); // giữ nguyên nội dung đã nhập
  }

  function handleReset() {
    setText("");
    replaceImage(null);
    setImageError(null);
    setFormError(null);
    setActiveSample(null);
    setResult(null);
    setError(null);
    setView("input");
  }

  return (
    <main className="flex flex-1 flex-col">
      {view === "input" && (
        <InputPanel
          text={text}
          onTextChange={handleTextChange}
          textareaRef={textareaRef}
          headingRef={headingRef}
          image={image}
          imageBusy={imageBusy}
          imageError={imageError}
          onPickFile={handlePickFile}
          onRemoveImage={() => replaceImage(null)}
          activeSampleTitle={activeSample?.title ?? null}
          hasUsedSample={nextSample > 0}
          onUseSample={handleUseSample}
          formError={formError}
          onSubmit={handleSubmit}
        />
      )}

      {view === "working" && (
        <ProgressScreen
          progress={progress}
          hasImage={image !== null}
          onCancel={handleCancel}
          headingRef={headingRef}
        />
      )}

      {view === "result" && result && (
        <ResultCard data={result} onReset={handleReset} headingRef={headingRef} />
      )}

      {view === "error" && error && (
        <ErrorPanel
          message={error.message}
          onRetry={handleSubmit}
          onEdit={() => setView("input")}
          headingRef={headingRef}
        />
      )}
    </main>
  );
}
