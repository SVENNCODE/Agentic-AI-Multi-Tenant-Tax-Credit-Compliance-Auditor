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
import { buildActionItems } from "@/lib/audit/actions";
import { formatStatus } from "@/lib/audit/types";

// Dashboard, this is for overview of the other screens only

function ReadinessRing({ percentage }: { percentage: number }) {
  return (
    <div
      className="relative h-24 w-24 shrink-0 rounded-full flex items-center justify-center"
      style={{
        background: `conic-gradient(#1B6E67 ${percentage * 3.6}deg, #254038 0deg)`,
      }}
    >
      <div className="h-[72px] w-[72px] rounded-full bg-[#0F1C1A] flex items-center justify-center">
        <span className="text-lg font-medium text-[#EAF1EF]">
          {percentage}%
        </span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const state = useAuditSummary();

  if (state.kind === "loading") return <LoadingState />;
  if (state.kind === "not_found") return <NotFoundState />;
  if (state.kind === "error") return <ErrorState message={state.message} />;

  const { data } = state;
  const openActions = buildActionItems(data).filter(
    (a) => a.priority !== "info",
  ).length;

  return (
    <PageShell>
      <PageHeading eyebrow="DASHBOARD" title={`Tax year ${data.tax_year}`} />

      {/* Readiness banner */}
      <div className="bg-[#0F1C1A] rounded-lg p-6 flex items-center gap-6">
        <ReadinessRing percentage={data.readiness_percentage} />
        <div>
          <p className="text-sm font-medium text-[#EAF1EF]">Filing readiness</p>
          <p className="text-xs text-[#8FA39E] mt-1">{data.readiness_note}</p>
        </div>
      </div>

      {/* Overview cards so each opens its dedicated screen */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          href="/audit"
          className="bg-white border border-[#E3E6EA] hover:border-[#1B6E67] rounded-lg p-4 transition-colors"
        >
          <p className="text-xs font-mono tracking-wide text-[#8B93A0]">
            RESIDENCY
          </p>
          <p className="text-base font-medium text-[#12161C] mt-2">
            {formatStatus(data.residency.status)}
          </p>
          <p className="text-xs text-[#5B6470] mt-1">
            {data.residency.target_form ?? "—"}
          </p>
          {data.residency.is_exempt_individual && (
            <p className="text-xs text-[#8B93A0] mt-2">
              {data.residency.exempt_years_used} of 5 exempt years used
            </p>
          )}
        </Link>

        <Link
          href="/audit"
          className="bg-white border border-[#E3E6EA] hover:border-[#1B6E67] rounded-lg p-4 transition-colors"
        >
          <p className="text-xs font-mono tracking-wide text-[#8B93A0]">
            CREDITS REVIEWED
          </p>
          <p className="text-base font-medium text-[#12161C] mt-2">
            {data.credits.total} evaluated
          </p>
          <div className="flex gap-3 mt-2 text-xs text-[#5B6470]">
            <span>{data.credits.eligible_count} eligible</span>
            <span>{data.credits.needs_documentation_count} pending</span>
          </div>
          <p className="text-xs text-[#1B6E67] mt-3">Open Credit Hub →</p>
        </Link>

        <Link
          href="/action-center"
          className="bg-white border border-[#E3E6EA] hover:border-[#1B6E67] rounded-lg p-4 transition-colors"
        >
          <p className="text-xs font-mono tracking-wide text-[#8B93A0]">
            ACTION CENTER
          </p>
          <p className="text-base font-medium text-[#12161C] mt-2">
            {openActions === 0
              ? "All clear"
              : `${openActions} open item${openActions === 1 ? "" : "s"}`}
          </p>
          <p className="text-xs text-[#5B6470] mt-1">{data.documents.note}</p>
          <p className="text-xs text-[#1B6E67] mt-3">Open Action Center →</p>
        </Link>
      </div>

      {data.explanation_report ? (
        <section className="bg-white border border-[#E3E6EA] rounded-lg p-6">
          <h2 className="text-sm font-medium text-[#12161C] mb-2">Summary</h2>
          <p className="text-sm text-[#5B6470]">
            {data.explanation_report.executive_summary}
          </p>
          <p className="text-xs text-[#8B93A0] border-t border-[#E3E6EA] pt-4 mt-4">
            {data.explanation_report.disclaimer}
          </p>
        </section>
      ) : (
        <section className="bg-white border border-[#E3E6EA] rounded-lg p-6">
          <p className="text-sm text-[#5B6470]">
            A written explanation isn&apos;t available for this submission yet,
            but the results were computed the same way regardless.
          </p>
        </section>
      )}
    </PageShell>
  );
}
