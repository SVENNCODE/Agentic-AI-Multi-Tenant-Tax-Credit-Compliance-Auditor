const STATUS_STYLES: Record<string, string> = {
  ELIGIBLE: "bg-emerald-50 text-emerald-700 border-emerald-200",
  NEEDS_DOCUMENTATION: "bg-amber-50 text-amber-700 border-amber-200",
  INELIGIBLE: "bg-slate-100 text-slate-500 border-slate-200",
  NOT_APPLICABLE: "bg-slate-100 text-slate-500 border-slate-200",
};

export function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.INELIGIBLE;
  return (
    <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full border ${style}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}
