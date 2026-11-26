import type { Ref } from "react";
import { WarningIcon } from "./icons";

interface Props {
  message: string;
  onRetry: () => void;
  onEdit: () => void;
  headingRef: Ref<HTMLHeadingElement>;
}

/**
 * Lỗi KHÔNG BAO GIỜ được hiểu là "không có gì đáng ngờ". Luôn nhắc đừng chuyển tiền khi chưa có kết quả.
 */
export default function ErrorPanel({ message, onRetry, onEdit, headingRef }: Props) {
  return (
    <section role="alert" aria-labelledby="error-title" className="flex flex-1 flex-col gap-5 pb-8">
      <div className="rounded-2xl border-2 border-red-700 bg-red-50 p-5">
        <div className="flex items-start gap-3">
          <WarningIcon className="mt-1 size-9 shrink-0 text-red-800" />
          <div>
            <h1
              id="error-title"
              ref={headingRef}
              tabIndex={-1}
              className="text-3xl font-extrabold leading-tight text-red-900 outline-none"
            >
              Chưa kiểm tra được
            </h1>
            <p className="mt-2 text-xl leading-relaxed">{message}</p>
          </div>
        </div>
      </div>

      <p className="rounded-2xl border-2 border-slate-400 bg-white p-5 text-xl font-semibold leading-relaxed">
        Chưa có kết quả nên chưa thể nói tin nhắn này an toàn. Xin đừng chuyển tiền cho đến khi kiểm tra xong.
      </p>

      <div className="mt-auto flex flex-col gap-3">
        <button
          type="button"
          onClick={onRetry}
          className="min-h-16 w-full rounded-2xl bg-blue-700 px-6 text-2xl font-extrabold text-white shadow-lg hover:bg-blue-800"
        >
          Thử lại
        </button>
        <button
          type="button"
          onClick={onEdit}
          className="min-h-14 w-full rounded-2xl border-2 border-slate-500 bg-white px-6 text-xl font-bold hover:bg-slate-100"
        >
          Quay lại sửa nội dung
        </button>
      </div>
    </section>
  );
}
