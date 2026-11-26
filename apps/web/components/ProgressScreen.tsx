"use client";

import { useEffect, useState, type Ref } from "react";
import type { EntityPreview, ProgressEvent, StageId } from "@/lib/api";
import EntityList from "./EntityList";
import { CheckIcon, SpinnerIcon } from "./icons";

/**
 * Trạng thái tiến trình CHỈ đổi khi máy chủ gửi sự kiện thật (xem lib/api.ts).
 * Không có đồng hồ nào tự "tick" bước sang bước, và tuyệt đối không có kết luận rủi ro sơ bộ.
 */
export interface ProgressState {
  /** Máy chủ đã gửi ít nhất một sự kiện tiến trình thật. */
  live: boolean;
  done: StageId[];
  entities: EntityPreview[];
}

export const INITIAL_PROGRESS: ProgressState = { live: false, done: [], entities: [] };

export function applyProgress(prev: ProgressState, event: ProgressEvent): ProgressState {
  return {
    live: true,
    done: prev.done.includes(event.done) ? prev.done : [...prev.done, event.done],
    entities: event.done === "entities" ? event.entities : prev.entities,
  };
}

const STEP_ORDER: readonly StageId[] = ["read", "entities", "evidence"];

function stepTitle(id: StageId, hasImage: boolean): string {
  switch (id) {
    case "read":
      return hasImage ? "Đọc chữ trong ảnh" : "Đọc tin nhắn";
    case "entities":
      return "Tìm số tài khoản, số điện thoại, đường link";
    case "evidence":
      return "Đối chiếu với danh sách cảnh báo";
  }
}

type StepState = "idle" | "done" | "active" | "pending";

function useElapsedSeconds(): number {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const start = performance.now();
    const id = setInterval(() => setSeconds(Math.floor((performance.now() - start) / 1000)), 500);
    return () => clearInterval(id);
  }, []);
  return seconds;
}

function Marker({ state, index }: { state: StepState; index: number }) {
  const base = "flex size-10 shrink-0 items-center justify-center rounded-full text-xl font-bold";
  if (state === "done") {
    return (
      <span className={`${base} bg-green-700 text-white`}>
        <CheckIcon className="size-6" />
      </span>
    );
  }
  if (state === "active") {
    return (
      <span className={`${base} bg-blue-700 text-white`}>
        <SpinnerIcon className="size-6" />
      </span>
    );
  }
  if (state === "pending") {
    return <span className={`${base} border-2 border-slate-400 text-slate-600`}>{index + 1}</span>;
  }
  return <span className={`${base} bg-slate-200 text-slate-800`}>{index + 1}</span>;
}

const STATUS_TEXT: Record<Exclude<StepState, "idle">, { text: string; className: string }> = {
  done: { text: "Xong", className: "text-green-800" },
  active: { text: "Đang làm…", className: "text-blue-800" },
  pending: { text: "Chờ", className: "text-slate-700" },
};

interface Props {
  progress: ProgressState;
  hasImage: boolean;
  onCancel: () => void;
  headingRef: Ref<HTMLHeadingElement>;
}

export default function ProgressScreen({ progress, hasImage, onCancel, headingRef }: Props) {
  const seconds = useElapsedSeconds();
  const { live, done, entities } = progress;

  const activeIndex = STEP_ORDER.findIndex((id) => !done.includes(id));

  function stateOf(index: number): StepState {
    if (!live) return "idle";
    if (done.includes(STEP_ORDER[index])) return "done";
    return index === activeIndex ? "active" : "pending";
  }

  const announce = !live
    ? "Đang kiểm tra. Vui lòng chờ."
    : activeIndex === -1
      ? "Đang hoàn tất kết quả."
      : `Đang làm: ${stepTitle(STEP_ORDER[activeIndex], hasImage)}.`;

  return (
    <section aria-labelledby="progress-title" className="flex flex-1 flex-col gap-5 pb-8">
      <div>
        <h1
          id="progress-title"
          ref={headingRef}
          tabIndex={-1}
          className="text-3xl font-extrabold leading-tight outline-none"
        >
          Đang kiểm tra…
        </h1>
        <p className="mt-2 text-xl text-slate-700">
          Thường mất vài giây. <strong className="text-slate-900">Xin đừng chuyển tiền trong lúc chờ.</strong>
        </p>
      </div>

      <div className="rounded-2xl border-2 border-slate-300 bg-white p-5">
        <p className="mb-4 text-xl font-bold">
          {live ? "Tiến trình" : "AI sẽ làm lần lượt 3 việc"}
        </p>

        <ol className="space-y-3">
          {STEP_ORDER.map((id, index) => {
            const state = stateOf(index);
            const status = state === "idle" ? null : STATUS_TEXT[state];
            return (
              <li
                key={id}
                aria-current={state === "active" ? "step" : undefined}
                className={`flex gap-3 rounded-xl p-3 ${state === "active" ? "bg-blue-50 ring-2 ring-blue-300" : ""}`}
              >
                <Marker state={state} index={index} />
                <div className="min-w-0 flex-1">
                  <p className={`text-xl leading-snug ${state === "pending" ? "text-slate-700" : "font-semibold"}`}>
                    {stepTitle(id, hasImage)}
                  </p>
                  {status && <p className={`font-bold ${status.className}`}>{status.text}</p>}

                  {id === "entities" && state === "done" && (
                    <div className="mt-2">
                      {entities.length > 0 ? (
                        <EntityList entities={entities} />
                      ) : (
                        <p className="text-slate-700">Không thấy số tài khoản hay đường link nào.</p>
                      )}
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ol>

        {/* Vùng đọc cho trình đọc màn hình: chỉ đổi khi tiến trình đổi, không đọc đồng hồ mỗi giây. */}
        <p role="status" className="sr-only">
          {announce}
        </p>
      </div>

      <div className="text-lg text-slate-700">
        {seconds >= 1 && <p>Đã chờ {seconds} giây.</p>}
        {seconds >= 15 && (
          <p className="mt-1 font-semibold text-slate-900">
            Lần này lâu hơn bình thường. Bạn có thể chờ thêm hoặc bấm “Dừng lại”.
          </p>
        )}
      </div>

      <button
        type="button"
        onClick={onCancel}
        className="mt-auto min-h-14 w-full rounded-2xl border-2 border-slate-500 bg-white px-6 text-xl font-bold text-slate-900 hover:bg-slate-100"
      >
        Dừng lại
      </button>
    </section>
  );
}
