"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { StatusBadge } from "@/components/audit/status-badge";
import {
  ErrorState,
  LoadingState,
  NotFoundState,
  PageHeading,
  PageShell,
} from "@/components/audit/page-states";
import { useAuditSummary } from "@/lib/audit/use-audit-summary";
import {
  SOURCE_LABELS,
  explanationFor,
  formatMoney,
  formatStatus,
  ruleLabel,
  type CreditItem,
  type CreditStatus,
} from "@/lib/audit/types";

// Screen 5 — Audit & Credit Discovery Hub.

type Filter = "ALL" | CreditStatus;

const FILTERS: { key: Filter; label: string }[] = [
  { key: "ALL", label: "All" },
  { key: "ELIGIBLE", label: "Eligible" },
  { key: "NEEDS_DOCUMENTATION", label: "Needs documentation" },
  { key: "INELIGIBLE", label: "Ineligible" },
  { key: "NOT_APPLICABLE", label: "Not applicable" },
];

const SOURCE_ORDER = ["FEDERAL_CREDIT", "NJ_DEDUCTION", "TREATY_BENEFIT"];

export default function AuditHubPage() {
  const state = useAuditSummary();
  const [filter, setFilter] = useState<Filter>("ALL");

  const items = useMemo(
    () => (state.kind === "ready" ? state.data.credits.items : []),
    [state],
  );

  const grouped = useMemo(() => {
    const visible =
      filter === "ALL" ? items : items.filter((i) => i.status === filter);
    const groups = new Map<string, CreditItem[]>();
    for (const item of visible) {
      const list = groups.get(item.source_type) ?? [];
      list.push(item);
      groups.set(item.source_type, list);
    }
    return [...groups.entries()].sort(
      ([a], [b]) => SOURCE_ORDER.indexOf(a) - SOURCE_ORDER.indexOf(b),
    );
  }, [items, filter]);

  if (state.kind === "loading") return <LoadingState />;
  if (state.kind === "not_found") return <NotFoundState />;
  if (state.kind === "error") return <ErrorState message={state.message} />;

  const { data } = state;
  const report = data.explanation_report;
  const eligibleTotal = items
    .filter((i) => i.status === "ELIGIBLE" && i.estimated_amount)
    .reduce((sum, i) => sum + (i.estimated_amount ?? 0), 0);
  const countFor = (f: Filter) =>
    f === "ALL" ? items.length : items.filter((i) => i.status === f).length;

  return (
    <PageShell>
      <PageHeading
        eyebrow="CREDIT HUB"
        title={`Audit & credit discovery tax year ${data.tax_year}`}
        subtitle="Every credit, deduction and treaty benefit checked, and why."
      />

      {/* Residency basis */}
      <section className="bg-white border border-[#E3E6EA] rounded-lg p-5">
        <p className="text-xs font-mono tracking-wide text-[#8B93A0]">
          RESIDENCY BASIS
        </p>
        <div className="flex flex-wrap items-baseline justify-between gap-2 mt-2">
          <p className="text-base font-medium text-[#12161C]">
            {formatStatus(data.residency.status)}
          </p>
          <p className="text-xs text-[#5B6470]">
            {data.residency.target_form ?? "—"}
          </p>
        </div>
        {report?.residency_breakdown && (
          <p className="text-sm text-[#5B6470] mt-3">
            {report.residency_breakdown}
          </p>
        )}
        {data.residency.audit_trail &&
          data.residency.audit_trail.length > 0 && (
            <details className="mt-3">
              <summary className="text-xs text-[#1B6E67] cursor-pointer">
                Show the rules that were applied
              </summary>
              <ol className="mt-2 space-y-2">
                {data.residency.audit_trail.map((step, i) => (
                  <li key={i} className="text-xs text-[#5B6470]">
                    <span
                      className={
                        step.passed ? "text-emerald-700" : "text-[#8B93A0]"
                      }
                    >
                      {step.passed ? "✓" : "✗"}
                    </span>{" "}
                    <span className="font-medium text-[#12161C]">
                      {step.rule}:
                    </span>{" "}
                    {step.details}
                  </li>
                ))}
              </ol>
            </details>
          )}
      </section>

      {/* Totals */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Evaluated", value: String(data.credits.total) },
          { label: "Eligible", value: String(data.credits.eligible_count) },
          {
            label: "Needs documentation",
            value: String(data.credits.needs_documentation_count),
          },
          { label: "Est. eligible value", value: formatMoney(eligibleTotal) },
        ].map((stat) => (
          <div
            key={stat.label}
            className="bg-white border border-[#E3E6EA] rounded-lg p-4"
          >
            <p className="text-xs text-[#8B93A0]">{stat.label}</p>
            <p className="text-lg font-medium text-[#12161C] mt-1">
              {stat.value}
            </p>
          </div>
        ))}
      </section>

      {/* Filters */}
      <div
        role="group"
        aria-label="Filter by status"
        className="flex flex-wrap gap-2"
      >
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => setFilter(f.key)}
            aria-pressed={filter === f.key}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              filter === f.key
                ? "bg-[#1B6E67] text-white border-[#1B6E67]"
                : "bg-white text-[#5B6470] border-[#E3E6EA] hover:border-[#1B6E67]"
            }`}
          >
            {f.label} ({countFor(f.key)})
          </button>
        ))}
      </div>

      {/* Grouped evaluations */}
      {grouped.length === 0 ? (
        <p className="text-sm text-[#5B6470]">
          No evaluations match this filter.
        </p>
      ) : (
        grouped.map(([source, list]) => (
          <section key={source}>
            <h2 className="text-sm font-medium text-[#12161C] mb-3">
              {SOURCE_LABELS[source] ?? source}
            </h2>
            <div className="space-y-2">
              {list.map((item, i) => {
                const explanation = explanationFor(item, report);
                return (
                  <article
                    key={`${source}-${i}`}
                    className="bg-white border border-[#E3E6EA] rounded-lg p-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-medium text-[#12161C]">
                        {ruleLabel(item)}
                      </span>
                      <StatusBadge status={item.status} />
                    </div>
                    <p className="text-sm text-[#5B6470] mt-2">{item.reason}</p>
                    {explanation && (
                      <p className="text-sm text-[#12161C] mt-2 border-l-2 border-[#D5E3E0] pl-3">
                        {explanation}
                      </p>
                    )}
                    {item.estimated_amount !== null &&
                      item.estimated_amount > 0 && (
                        <p className="text-xs text-[#8B93A0] mt-2">
                          Estimated amount: {formatMoney(item.estimated_amount)}
                        </p>
                      )}
                  </article>
                );
              })}
            </div>
          </section>
        ))
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#E3E6EA] pt-6">
        <p className="text-xs text-[#8B93A0] max-w-md">
          {report?.disclaimer ??
            "Estimates are approximate and are not tax advice. Consult a qualified tax professional before filing."}
        </p>
        <Link
          href="/action-center"
          className="bg-[#1B6E67] hover:bg-[#16564F] text-white text-sm px-4 py-2 rounded-md"
        >
          Go to Action Center →
        </Link>
      </div>
    </PageShell>
  );
}
