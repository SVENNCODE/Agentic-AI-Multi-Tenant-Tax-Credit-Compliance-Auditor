"use client";

import Link from "next/link";
import {
  ErrorState,
  LoadingState,
  NotFoundState,
  PageHeading,
  PageShell,
} from "@/components/audit/page-states";
import { useAuditSummary } from "@/lib/audit/use-audit-summary";
import { formatStatus } from "@/lib/audit/types";
import {
  buildActionItems,
  buildReadinessChecklist,
  type ActionPriority,
} from "@/lib/audit/actions";

// Screen 6 Readiness Report / Action Center.
const PRIORITY_STYLES: Record<
  ActionPriority,
  { label: string; className: string }
> = {
  high: {
    label: "Priority",
    className: "bg-[#FBEAE6] text-[#B3432F] border-[#F0C7BC]",
  },
  medium: {
    label: "To do",
    className: "bg-amber-50 text-amber-700 border-amber-200",
  },
  info: {
    label: "Tip",
    className: "bg-slate-100 text-slate-600 border-slate-200",
  },
};

export default function ActionCenterPage() {
  const state = useAuditSummary();

  if (state.kind === "loading") return <LoadingState />;
  if (state.kind === "not_found") return <NotFoundState />;
  if (state.kind === "error") return <ErrorState message={state.message} />;

  const { data } = state;
  const actions = buildActionItems(data);
  const checklist = buildReadinessChecklist(data);
  const openCount = actions.filter((a) => a.priority !== "info").length;

  return (
    <PageShell>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <PageHeading
          eyebrow="ACTION CENTER"
          title={`Readiness report — tax year ${data.tax_year}`}
          subtitle={
            openCount === 0
              ? "No open action items. Review the tips below before filing."
              : `${openCount} item${openCount === 1 ? "" : "s"} need your attention before filing.`
          }
        />
        <button
          type="button"
          onClick={() => window.print()}
          className="text-sm border border-[#E3E6EA] bg-white hover:border-[#1B6E67] text-[#12161C] px-3 py-1.5 rounded-md print:hidden"
        >
          Print report
        </button>
      </div>

      {/* Readiness summary */}
      <section className="bg-[#0F1C1A] rounded-lg p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[#EAF1EF]">
              Filing readiness
            </p>
            <p className="text-xs text-[#8FA39E] mt-1">{data.readiness_note}</p>
          </div>
          <p className="text-3xl font-medium text-[#EAF1EF]">
            {data.readiness_percentage}%
          </p>
        </div>
        <div
          className="h-2 rounded-full bg-[#254038] mt-4 overflow-hidden"
          role="progressbar"
          aria-valuenow={data.readiness_percentage}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Filing readiness"
        >
          <div
            className="h-full bg-[#1B6E67]"
            style={{ width: `${data.readiness_percentage}%` }}
          />
        </div>
        <p className="text-xs text-[#8FA39E] mt-3">
          Residency: {formatStatus(data.residency.status)} ·{" "}
          {data.residency.target_form ?? "—"}
        </p>
      </section>

      {/* Checklist */}
      <section className="bg-white border border-[#E3E6EA] rounded-lg p-5">
        <h2 className="text-sm font-medium text-[#12161C] mb-3">
          Readiness checklist
        </h2>
        <ul className="space-y-2">
          {checklist.map((c) => (
            <li
              key={c.label}
              className="flex items-start justify-between gap-3 text-sm"
            >
              <span className="flex items-start gap-2">
                <span
                  aria-hidden
                  className={c.done ? "text-emerald-700" : "text-[#A0A7B0]"}
                >
                  {c.done ? "✓" : "○"}
                </span>
                <span className={c.done ? "text-[#12161C]" : "text-[#5B6470]"}>
                  {c.label}
                  <span className="sr-only">
                    {c.done ? " (complete)" : " (incomplete)"}
                  </span>
                </span>
              </span>
              {c.note && (
                <span className="text-xs text-[#8B93A0] text-right">
                  {c.note}
                </span>
              )}
            </li>
          ))}
        </ul>
      </section>

      {/* Action items */}
      <section>
        <h2 className="text-sm font-medium text-[#12161C] mb-3">
          Action items
        </h2>
        {actions.length === 0 ? (
          <p className="text-sm text-[#5B6470]">Nothing to do right now.</p>
        ) : (
          <ol className="space-y-2">
            {actions.map((a) => {
              const p = PRIORITY_STYLES[a.priority];
              return (
                <li
                  key={a.id}
                  className="bg-white border border-[#E3E6EA] rounded-lg p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium text-[#12161C]">
                      {a.title}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full border ${p.className}`}
                    >
                      {p.label}
                    </span>
                  </div>
                  <p className="text-sm text-[#5B6470] mt-2">{a.detail}</p>
                  {a.href && (
                    <Link
                      href={a.href}
                      className="inline-block text-xs text-[#1B6E67] hover:underline mt-2 print:hidden"
                    >
                      {a.hrefLabel ?? "Open"} →
                    </Link>
                  )}
                </li>
              );
            })}
          </ol>
        )}
      </section>

      <p className="text-xs text-[#8B93A0] border-t border-[#E3E6EA] pt-4">
        {data.explanation_report?.disclaimer ??
          "This report is based on the information you provided and is not tax or legal advice. Consult a qualified tax professional before filing."}
      </p>
    </PageShell>
  );
}
