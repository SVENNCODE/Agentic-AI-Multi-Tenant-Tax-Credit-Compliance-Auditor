"use client";

type Props = {
  result: Record<string, unknown> | null;
  error: string | null;
  isSubmitting: boolean;
};

export function ReviewStep({ result, error, isSubmitting }: Props) {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-[#12161C] mb-2">
        Review & submit
      </h3>
      <p className="text-xs text-[#8B93A0]">
        Submitting runs your residency determination. This shows the raw result
        for now, the dashboard will present this the same way it shows every
        other audit metric once it&apos;s built.
      </p>

      {isSubmitting && (
        <p className="text-sm text-[#5B6470]">Running residency check…</p>
      )}

      {error && (
        <p
          role="alert"
          className="text-sm text-[#B3432F] bg-[#FBEAE6] border border-[#F0C7BC] rounded-md px-3 py-2"
        >
          {error}
        </p>
      )}

      {result && (
        <pre className="text-xs bg-[#0F1C1A] text-[#EAF1EF] rounded-md p-4 overflow-x-auto">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
