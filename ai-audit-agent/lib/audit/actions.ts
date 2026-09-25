import { ruleLabel, type AuditSummary } from "./types";

export type ActionPriority = "high" | "medium" | "info";

export type ActionItem = {
  id: string;
  priority: ActionPriority;
  title: string;
  detail: string;
  href?: string;
  hrefLabel?: string;
};
export function buildActionItems(data: AuditSummary): ActionItem[] {
  const items: ActionItem[] = [];
  const status = data.residency.status;

  if (status === "UNDETERMINED") {
    items.push({
      id: "residency-undetermined",
      priority: "high",
      title: "Fix your residency inputs",
      detail:
        "Your residency status couldn't be determined from your answers (for example a missing entry date or conflicting visa periods). Most credits depend on it.",
      href: "/questionnaire",
      hrefLabel: "Review questionnaire",
    });
  } else if (status === "DUAL_STATUS") {
    items.push({
      id: "residency-dual",
      priority: "high",
      title: "Get professional review for a dual-status year",
      detail:
        "Your status changed during the year. Dual-status returns (Form 1040 + 1040-NR) need a tax professional's review.",
    });
  } else if (!data.residency.determined) {
    items.push({
      id: "residency-missing",
      priority: "high",
      title: "Complete the questionnaire",
      detail: "No residency determination exists for this tax year yet.",
      href: "/questionnaire",
      hrefLabel: "Start questionnaire",
    });
  }

  data.credits.items
    .filter((c) => c.status === "NEEDS_DOCUMENTATION")
    .forEach((c, i) => {
      items.push({
        id: `doc-${i}`,
        priority: "medium",
        title: `Resolve: ${ruleLabel(c)}`,
        detail: c.reason,
        href: "/audit",
        hrefLabel: "See details",
      });
    });

  (data.explanation_report?.next_steps ?? []).forEach((step, i) => {
    items.push({
      id: `next-${i}`,
      priority: "info",
      title: "Suggested next step",
      detail: step,
    });
  });

  if (!data.documents.available) {
    items.push({
      id: "documents",
      priority: "info",
      title: "Gather your tax documents",
      detail:
        "Document upload isn't available yet. Keep your W-2/1042-S, 1098-T, I-20/DS-2019 and passport entry records ready for filing.",
    });
  }

  return items;
}

export type ReadinessCheck = { label: string; done: boolean; note?: string };

export function buildReadinessChecklist(data: AuditSummary): ReadinessCheck[] {
  const residencyOk =
    data.residency.determined &&
    data.residency.status !== "UNDETERMINED" &&
    data.residency.status !== null;
  return [
    {
      label: "Residency status determined",
      done: residencyOk,
      note: data.residency.target_form ?? undefined,
    },
    {
      label: "Credits & deductions evaluated",
      done: data.credits.evaluated,
      note: `${data.credits.total} checked`,
    },
    {
      label: "No open documentation items",
      done: data.credits.needs_documentation_count === 0,
      note:
        data.credits.needs_documentation_count > 0
          ? `${data.credits.needs_documentation_count} open`
          : undefined,
    },
    {
      label: "Supporting documents uploaded",
      done: false,
      note: "Not available yet",
    },
  ];
}
