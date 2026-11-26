import type { Ref } from "react";
import {
  ACTION_TEXT,
  EVIDENCE_SOURCE,
  GROUP_NAME,
  RISK,
  TACTIC,
  labelOf,
} from "@/lib/labels";
import type { Analysis, RiskLevel } from "@/lib/types";
import EntityList from "./EntityList";
import { InfoIcon, QuestionIcon, WarningIcon } from "./icons";

function RiskIcon({ level, className }: { level: RiskLevel; className?: string }) {
  if (level === "uncertain") return <QuestionIcon className={className} />;
  if (level === "low") return <InfoIcon className={className} />;
  return <WarningIcon className={className} />;
}

interface Props {
  data: Analysis;
  onReset: () => void;
  headingRef: Ref<HTMLHeadingElement>;
}

/**
 * Thẻ kết quả. Mọi nội dung đến từ JSON theo analysis.schema.json.
 * Client chỉ ĐỔI TÊN enum sang tiếng Việt (lib/labels.ts), không tự tính hay sửa mức nguy cơ.
 */
export default function ResultCard({ data, onReset, headingRef }: Props) {
  const risk = RISK[data.risk_level];
  const action = ACTION_TEXT[data.recommended_action];
  const group = data.scenario_group ? GROUP_NAME[data.scenario_group] : null;
  const entities = (data.entities ?? []).flatMap((e) =>
    e.display ? [{ type: e.type, display: e.display }] : [],
  );

  return (
    <article aria-labelledby="result-title" className="flex flex-1 flex-col gap-5 pb-8">
      <header className={`rounded-2xl border-2 p-5 ${risk.banner}`}>
        <div className="flex items-start gap-3">
          <RiskIcon level={data.risk_level} className="mt-1 size-10 shrink-0" />
          <div>
            <h1
              id="result-title"
              ref={headingRef}
              tabIndex={-1}
              className="text-3xl font-extrabold leading-tight outline-none"
            >
              {risk.label}
            </h1>
            <p className="mt-1 text-xl font-medium">{risk.hint}</p>
            <p className="mt-2 font-semibold">Điểm rủi ro: {data.risk_score}/100</p>
          </div>
        </div>
      </header>

      <section className="rounded-2xl border-2 border-slate-300 bg-white p-5">
        <p className="text-xl leading-relaxed">{data.summary}</p>
        {group && (
          <p className="mt-3 text-slate-700">
            Giống thủ đoạn: <strong className="text-slate-900">{group}</strong>
          </p>
        )}
      </section>

      <section className="rounded-2xl border-2 border-blue-700 bg-blue-50 p-5">
        <h2 className="text-lg font-bold uppercase tracking-wide text-blue-900">Việc nên làm</h2>
        <p className="mt-1 text-2xl font-extrabold leading-snug text-slate-900">{action.title}</p>
        <p className="mt-2 text-xl leading-relaxed">{action.body}</p>
      </section>

      <section aria-labelledby="flags-title" className="rounded-2xl border-2 border-slate-300 bg-white p-5">
        <h2 id="flags-title" className="text-2xl font-bold">
          Dấu hiệu đáng ngờ
        </h2>
        {data.red_flags.length > 0 ? (
          <ol className="mt-4 space-y-5">
            {data.red_flags.map((flag, i) => (
              <li key={i} className="flex gap-3">
                <span
                  aria-hidden="true"
                  className="flex size-9 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xl font-bold text-white"
                >
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  {flag.tactic && flag.tactic !== "other" && (
                    <p className="mb-1 inline-block rounded-md bg-slate-100 px-2 py-0.5 font-bold text-slate-900">
                      {labelOf(TACTIC, flag.tactic)}
                    </p>
                  )}
                  <blockquote className="border-l-4 border-slate-400 pl-3 text-xl font-semibold italic leading-snug">
                    “{flag.quote}”
                  </blockquote>
                  <p className="mt-2 text-xl leading-relaxed">{flag.reason}</p>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="mt-3 text-xl text-slate-700">AI không nêu dấu hiệu đáng ngờ cụ thể nào.</p>
        )}
      </section>

      {data.verification_questions.length > 0 && (
        <section aria-labelledby="questions-title" className="rounded-2xl border-2 border-slate-300 bg-white p-5">
          <h2 id="questions-title" className="text-2xl font-bold">
            Hãy tự hỏi trước khi chuyển tiền
          </h2>
          <ul className="mt-3 space-y-3">
            {data.verification_questions.map((q, i) => (
              <li key={i} className="flex gap-3 text-xl leading-relaxed">
                <QuestionIcon className="mt-1 size-6 shrink-0 text-blue-700" />
                <span>{q}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {entities.length > 0 && (
        <section aria-labelledby="entities-title" className="rounded-2xl border-2 border-slate-300 bg-white p-5">
          <h2 id="entities-title" className="text-2xl font-bold">
            Thông tin tìm thấy trong tin nhắn
          </h2>
          <div className="mt-3">
            <EntityList entities={entities} />
          </div>
        </section>
      )}

      {data.evidence.length > 0 && (
        <details open className="rounded-2xl border-2 border-slate-300 bg-white p-5">
          <summary className="cursor-pointer text-2xl font-bold">
            Bằng chứng đã tra cứu ({data.evidence.length})
          </summary>
          <ul className="mt-4 space-y-4">
            {data.evidence.map((item, i) => (
              <li key={i}>
                <p className="font-bold text-slate-900">{labelOf(EVIDENCE_SOURCE, item.source)}</p>
                <p className="text-xl leading-relaxed">{item.finding}</p>
              </li>
            ))}
          </ul>
        </details>
      )}

      {/* Câu bắt buộc của dự án. Lấy từ JSON (schema đặt const), luôn hiển thị. */}
      <p role="note" className="flex gap-3 rounded-2xl border-2 border-slate-400 bg-slate-100 p-5 text-xl leading-relaxed">
        <InfoIcon className="mt-1 size-6 shrink-0 text-slate-700" />
        <span>{data.ai_disclaimer}</span>
      </p>

      {typeof data.latency_ms === "number" && (
        <p className="text-slate-700">Phân tích trong {(data.latency_ms / 1000).toFixed(1).replace(".", ",")} giây.</p>
      )}

      <button
        type="button"
        onClick={onReset}
        className="mt-auto min-h-16 w-full rounded-2xl bg-blue-700 px-6 text-2xl font-extrabold text-white shadow-lg hover:bg-blue-800"
      >
        Kiểm tra tin khác
      </button>
    </article>
  );
}
