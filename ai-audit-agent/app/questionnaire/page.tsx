"use client";

import { useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { AppNav } from "@/components/app-nav";
import { createClient } from "@/lib/utils/supabase/client";
import {
  questionnaireSchema,
  type QuestionnaireInput,
} from "@/lib/utils/validation/questionnaire";
import { ProfileStep } from "./steps/ProfileStep";
import { IncomeStep } from "./steps/IncomeStep";
import { ExpensesStep } from "./steps/ExpensesStep";
import { ReviewStep } from "./steps/ReviewStep";

const STEPS = ["Profile", "Income", "Expenses", "Review"] as const;

// Note for me: Fields validated at each step before letting the user continue keeps
// errors scoped to the step they're actually on instead of validating the
// whole form at once.
const STEP_FIELDS: Record<number, (keyof QuestionnaireInput)[]> = {
  0: [
    "state_of_residence",
    "filing_status",
    "citizenship_country",
    "us_entry_date",
    "current_visa_type",
    "employment_type",
    "is_fulltime_student",
    "visa_status_periods",
  ],
  1: [
    "days_present_current_year",
    "days_present_prior_year",
    "days_present_two_years_prior",
    "annual_income",
    "number_of_employers",
  ],
  2: [
    "has_education_expenses",
    "has_childcare_expenses",
    "has_medical_expenses",
    "has_charitable_donations",
    "has_retirement_contributions",
    "scholarship_amount",
    "tuition_paid",
    "tuition_paid_to_nj",
    "prior_years_aotc_claimed",
  ],
};

const CURRENT_TAX_YEAR = new Date().getFullYear() - 1;

export default function QuestionnairePage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const methods = useForm<QuestionnaireInput>({
    resolver: zodResolver(questionnaireSchema),
    defaultValues: {
      tax_year: CURRENT_TAX_YEAR,
      state_of_residence: "NJ",
      filing_status: "SINGLE",
      current_visa_type: "F1",
      employment_type: "W2",
      is_fulltime_student: true,
      visa_status_periods: [
        {
          visa_type: "F1",
          start_date: "",
          end_date: "",
          is_exempt_status: true,
        },
      ],
      annual_income: 0,
      number_of_employers: 1,
      scholarship_amount: 0,
      tuition_paid: 0,
      has_education_expenses: false,
      has_childcare_expenses: false,
      has_medical_expenses: false,
      has_charitable_donations: false,
      has_retirement_contributions: false,
    },
  });

  async function goNext() {
    const fieldsToValidate = STEP_FIELDS[step];
    const valid = fieldsToValidate
      ? await methods.trigger(fieldsToValidate)
      : true;
    if (valid) setStep((s) => Math.min(s + 1, STEPS.length - 1));
  }

  function goBack() {
    setStep((s) => Math.max(s - 1, 0));
  }

  async function onSubmit(data: QuestionnaireInput) {
    setIsSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setError("Your session expired — please sign in again.");
        setIsSubmitting(false);
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/questionnaire/save`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify(data),
        },
      );

      if (response.status === 429) {
        setError(
          "You've submitted several times in a short period. Please wait a minute and try again.",
        );
        return;
      }

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        const detail =
          typeof body?.detail === "string"
            ? body.detail
            : response.status === 422
              ? "Some answers are invalid. Please review each step and try again."
              : "Something went wrong. Please try again.";
        setError(detail);
        return;
      }

      const body = await response.json();
      setResult(body);
      // Results are persisted server-side; the dashboard is the canonical view.
      router.push("/dashboard");
    } catch {
      setError("Could not reach the server. Check your connection.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const isReviewStep = step === STEPS.length - 1;

  return (
    <div className="min-h-screen bg-[#F7F8FA]">
      <AppNav />
      <div className="max-w-2xl mx-auto px-6 py-12">
        <span className="font-mono text-xs tracking-[0.2em] text-[#5C7C74]">
          INTAKE
        </span>
        <h1 className="text-xl font-medium text-[#12161C] mt-2">
          Tell us about your situation
        </h1>
        <p className="text-sm text-[#5B6470] mt-1">
          Tax year {CURRENT_TAX_YEAR}. This determines residency status and
          which credits could apply.
        </p>

        {/* Step indicator */}
        <ol className="flex items-center gap-2 mt-8 mb-8">
          {STEPS.map((label, i) => (
            <li key={label} className="flex items-center gap-2 flex-1">
              <div
                className={`h-1 w-full rounded-full ${
                  i <= step ? "bg-[#1B6E67]" : "bg-[#E3E6EA]"
                }`}
              />
            </li>
          ))}
        </ol>
        <p className="font-mono text-xs text-[#5C7C74] -mt-6 mb-8">
          {String(step + 1).padStart(2, "0")} / {STEPS.length} — {STEPS[step]}
        </p>

        <FormProvider {...methods}>
          <form
            onSubmit={
              isReviewStep
                ? methods.handleSubmit(onSubmit)
                : (e) => e.preventDefault()
            }
            className="bg-white border border-[#E3E6EA] rounded-lg p-6"
          >
            {step === 0 && <ProfileStep />}
            {step === 1 && <IncomeStep />}
            {step === 2 && <ExpensesStep />}
            {step === 3 && (
              <ReviewStep
                result={result}
                error={error}
                isSubmitting={isSubmitting}
              />
            )}

            <div className="flex justify-between mt-8">
              <Button
                type="button"
                variant="outline"
                onClick={goBack}
                disabled={step === 0}
              >
                Back
              </Button>

              {isReviewStep ? (
                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="bg-[#1B6E67] hover:bg-[#16564F] text-white"
                >
                  {isSubmitting ? "Submitting…" : "Submit"}
                </Button>
              ) : (
                <Button
                  type="button"
                  onClick={goNext}
                  className="bg-[#1B6E67] hover:bg-[#16564F] text-white"
                >
                  Continue
                </Button>
              )}
            </div>
          </form>
        </FormProvider>
      </div>
    </div>
  );
}
