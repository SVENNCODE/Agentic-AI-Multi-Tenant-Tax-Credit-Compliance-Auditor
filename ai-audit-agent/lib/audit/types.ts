export type CreditStatus =
  | "ELIGIBLE"
  | "NEEDS_DOCUMENTATION"
  | "INELIGIBLE"
  | "NOT_APPLICABLE";

export type SourceType = "FEDERAL_CREDIT" | "NJ_DEDUCTION" | "TREATY_BENEFIT";

export type CreditItem = {
  source_type: SourceType | string;
  federal_credit_code: string | null;
  nj_rule_code: string | null;
  treaty_country_code: string | null;
  status: CreditStatus;
  reason: string;
  estimated_amount: number | null;
};

export type CreditExplanation = {
  rule_code: string;
  status: string;
  explanation: string;
};

export type ExplanationReport = {
  executive_summary: string;
  residency_breakdown: string;
  credit_breakdown: CreditExplanation[];
  next_steps: string[];
  disclaimer: string;
};

export type ResidencyStatus =
  | "NONRESIDENT_ALIEN"
  | "RESIDENT_ALIEN"
  | "DUAL_STATUS"
  | "UNDETERMINED";

export type AuditSummary = {
  tax_year: number;
  readiness_percentage: number;
  readiness_note: string;
  residency: {
    determined: boolean;
    status: ResidencyStatus | null;
    target_form: string | null;
    is_exempt_individual: boolean | null;
    exempt_years_used: number | null;
    audit_trail: { rule: string; passed: boolean; details: string }[] | null;
  };
  credits: {
    evaluated: boolean;
    total: number;
    eligible_count: number;
    needs_documentation_count: number;
    ineligible_count: number;
    items: CreditItem[];
  };
  documents: { available: boolean; note: string };
  explanation_report: ExplanationReport | null;
};

export const SOURCE_LABELS: Record<string, string> = {
  FEDERAL_CREDIT: "Federal credits",
  NJ_DEDUCTION: "New Jersey deductions",
  TREATY_BENEFIT: "Tax treaty benefits",
};

export function ruleLabel(item: CreditItem): string {
  return (
    item.federal_credit_code ??
    item.nj_rule_code ??
    (item.treaty_country_code
      ? `Treaty (${item.treaty_country_code})`
      : null) ??
    "—"
  );
}
export function explanationFor(
  item: CreditItem,
  report: ExplanationReport | null,
): string | null {
  if (!report) return null;
  const code = item.federal_credit_code ?? item.nj_rule_code;
  const match = report.credit_breakdown.find((c) => {
    if (code) return c.rule_code === code;
    if (item.source_type === "TREATY_BENEFIT") {
      const country = item.treaty_country_code ?? "";
      return (
        c.rule_code === "TREATY_NOT_EVALUATED" ||
        (country !== "" && c.rule_code.startsWith(`US_${country}_`))
      );
    }
    return false;
  });
  return match?.explanation ?? null;
}

export function formatStatus(status: string | null | undefined): string {
  return status ? status.replaceAll("_", " ") : "Not determined";
}

export function formatMoney(n: number): string {
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}
