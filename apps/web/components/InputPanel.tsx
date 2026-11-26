"use client";

import { useState, type ClipboardEvent, type DragEvent, type FormEvent, type Ref } from "react";
import type { PreparedImage } from "@/lib/image";
import { DocumentIcon, PhotoIcon, SpinnerIcon } from "./icons";

interface Props {
  text: string;
  onTextChange: (value: string) => void;
  textareaRef: Ref<HTMLTextAreaElement>;
  headingRef: Ref<HTMLHeadingElement>;

  image: PreparedImage | null;
  imageBusy: boolean;
  imageError: string | null;
  onPickFile: (file: File) => void;
  onRemoveImage: () => void;

  /** Tên mẫu đang điền trong ô nhập; null khi người dùng đã tự sửa hoặc chưa dùng mẫu. */
  activeSampleTitle: string | null;
  hasUsedSample: boolean;
  onUseSample: () => void;

  formError: string | null;
  onSubmit: () => void;
}

export default function InputPanel(props: Props) {
  const {
    text,
    onTextChange,
    textareaRef,
    headingRef,
    image,
    imageBusy,
    imageError,
    onPickFile,
    onRemoveImage,
    activeSampleTitle,
    hasUsedSample,
    onUseSample,
    formError,
    onSubmit,
  } = props;

  const [dragging, setDragging] = useState(false);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSubmit();
  }

  function handleDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onPickFile(file);
  }

  // Dán ảnh chụp màn hình thẳng vào ô nhập (máy tính): Ctrl+V.
  function handlePaste(e: ClipboardEvent<HTMLTextAreaElement>) {
    const file = Array.from(e.clipboardData.files).find((f) => f.type.startsWith("image/"));
    if (file) {
      e.preventDefault();
      onPickFile(file);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-1 flex-col gap-4">
      <div>
        <h1
          ref={headingRef}
          tabIndex={-1}
          className="text-2xl font-extrabold leading-tight text-balance outline-none"
        >
          Kiểm tra trước khi chuyển tiền
        </h1>
        {/* Chỉ hiện khi màn hình đủ cao, để khu thả ảnh luôn nằm trong màn hình đầu tiên. */}
        <p className="mt-1 hidden text-xl text-slate-700 [@media(min-height:760px)]:block">
          Dán tin nhắn hoặc chọn ảnh chụp màn hình. AI sẽ chỉ ra dấu hiệu lừa đảo, nếu có.
        </p>
      </div>

      {/* Nút "Dùng mẫu" ngay đầu trang để người chấm thử được trong 10 giây đầu. */}
      <div>
        <button
          type="button"
          onClick={onUseSample}
          className="flex min-h-14 w-full items-center justify-center gap-2 rounded-xl border-2 border-blue-700 bg-blue-50 px-4 text-xl font-bold text-blue-800 hover:bg-blue-100"
        >
          <DocumentIcon className="size-6 shrink-0" />
          {hasUsedSample ? "Dùng mẫu khác" : "Dùng mẫu"}
        </button>
        <p className="mt-2 text-balance text-slate-800">Điền sẵn tin nhắn mẫu. AI vẫn phân tích thật.</p>
      </div>

      <div>
        <label htmlFor="message" className="mb-1 block text-xl font-bold">
          Tin nhắn cần kiểm tra
        </label>
        {/* field-sizing: tự giãn theo nội dung ở trình duyệt hỗ trợ; nơi khác dùng rows và cuộn. */}
        <textarea
          id="message"
          ref={textareaRef}
          rows={3}
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          onPaste={handlePaste}
          placeholder="Dán nội dung tin nhắn vào đây…"
          className="field-sizing-content max-h-72 min-h-[7.5rem] w-full resize-y rounded-xl border-2 border-slate-500 bg-white px-4 py-3 text-xl leading-relaxed placeholder:text-slate-600"
        />
        <div role="status" aria-live="polite">
          {activeSampleTitle && (
            <p className="mt-2 rounded-lg bg-blue-100 px-3 py-2 font-semibold text-blue-950">
              Đang dùng mẫu: {activeSampleTitle}. Bấm “Kiểm tra” để AI phân tích.
            </p>
          )}
        </div>
      </div>

      <div>
        <p className="mb-1 text-xl font-bold">Hoặc chọn ảnh chụp tin nhắn</p>

        {image ? (
          <div className="flex gap-3 rounded-2xl border-2 border-slate-400 bg-white p-3">
            {/* Ảnh xem trước là blob: URL cục bộ nên không dùng next/image. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={image.previewUrl}
              alt="Ảnh chụp tin nhắn bạn đã chọn"
              className="h-28 w-20 shrink-0 rounded-lg bg-slate-100 object-cover object-top"
            />
            <div className="flex min-w-0 flex-1 flex-col justify-between gap-2">
              <div className="min-w-0">
                <p className="font-bold">Đã chọn ảnh</p>
                <p className="truncate text-slate-700">{image.name}</p>
              </div>
              <button
                type="button"
                onClick={onRemoveImage}
                className="min-h-12 w-full rounded-xl border-2 border-slate-500 bg-white px-4 font-bold hover:bg-slate-100"
              >
                Bỏ ảnh
              </button>
            </div>
          </div>
        ) : (
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            className={`flex min-h-24 cursor-pointer flex-col items-center justify-center gap-0.5 rounded-2xl border-2 border-dashed px-4 py-3 text-center has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-3 has-[:focus-visible]:outline-blue-700 ${
              dragging ? "border-blue-700 bg-blue-100" : "border-slate-500 bg-white hover:bg-slate-50"
            }`}
          >
            <input
              type="file"
              accept="image/*"
              className="sr-only"
              onChange={(e) => {
                const file = e.target.files?.[0];
                e.target.value = ""; // cho phép chọn lại đúng tệp đó lần sau
                if (file) onPickFile(file);
              }}
            />
            {imageBusy ? (
              <>
                <SpinnerIcon className="size-10 text-blue-700" />
                <span className="text-xl font-bold">Đang chuẩn bị ảnh…</span>
              </>
            ) : (
              <>
                <PhotoIcon className="size-8 text-blue-700" />
                <span className="text-xl font-bold">Chạm để chọn ảnh</span>
                <span className="hidden text-slate-700 sm:inline">hoặc kéo thả ảnh vào đây</span>
              </>
            )}
          </label>
        )}

        {imageError && (
          <p role="alert" className="mt-2 font-semibold text-red-800">
            {imageError}
          </p>
        )}
      </div>

      {/* Nút chính dính đáy màn hình: luôn thấy được dù trang dài hay điện thoại nhỏ. */}
      <div className="sticky bottom-0 -mx-4 mt-auto bg-linear-to-t from-slate-50 via-slate-50 to-transparent px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
        {formError && (
          <p role="alert" className="mb-3 rounded-xl border-2 border-red-700 bg-red-50 p-3 font-semibold text-red-900">
            {formError}
          </p>
        )}
        <button
          type="submit"
          disabled={imageBusy}
          className="min-h-16 w-full rounded-2xl bg-blue-700 px-6 text-2xl font-extrabold text-white shadow-lg hover:bg-blue-800 disabled:bg-slate-600"
        >
          {imageBusy ? "Đang chuẩn bị ảnh…" : "Kiểm tra"}
        </button>
      </div>
    </form>
  );
}
