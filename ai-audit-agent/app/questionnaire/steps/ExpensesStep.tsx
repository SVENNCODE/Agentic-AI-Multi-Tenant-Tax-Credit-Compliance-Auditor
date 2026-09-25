"use client";

import { useFormContext, Controller, useWatch } from "react-hook-form";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import type { QuestionnaireInput } from "@/lib/utils/validation/questionnaire";

const EXPENSE_FIELDS: { name: keyof QuestionnaireInput; label: string }[] = [
  {
    name: "has_education_expenses",
    label: "Education expenses (Tuition, fees, books)",
  },
  { name: "has_childcare_expenses", label: "Childcare" },
  { name: "has_medical_expenses", label: "Medical expenses" },
  { name: "has_charitable_donations", label: "Charitable donations" },
  { name: "has_retirement_contributions", label: "Retirement contributions" },
];

export function ExpensesStep() {
  const {
    control,
    register,
    formState: { errors },
  } = useFormContext<QuestionnaireInput>();

  const hasEducationExpenses = useWatch({
    control,
    name: "has_education_expenses",
  });

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        {EXPENSE_FIELDS.map((field) => (
          <div key={field.name} className="flex items-center gap-2">
            <Controller
              name={field.name}
              control={control}
              render={({ field: { value, onChange } }) => (
                <Checkbox
                  id={field.name}
                  checked={!!value}
                  onCheckedChange={onChange}
                />
              )}
            />
            <Label htmlFor={field.name} className="font-normal cursor-pointer">
              {field.label}
            </Label>
          </div>
        ))}
      </div>

      {hasEducationExpenses && (
        <div className="p-4 border border-border rounded-lg bg-muted/30 space-y-4 animate-in fade-in-50">
          <h4 className="font-medium text-sm text-foreground">
            Higher Education Details
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="tuition_paid">
                Tuition Paid ($) <span className="text-destructive">*</span>
              </Label>
              <Input
                id="tuition_paid"
                type="number"
                min="0"
                step="0.01"
                placeholder="e.g. 12000"
                {...register("tuition_paid", { valueAsNumber: true })}
              />
              <p className="text-xs text-muted-foreground">
                Total tuition and required fees paid to the institution, before
                subtracting any scholarship (1098-T Box 1).
              </p>
              {errors.tuition_paid && (
                <p className="text-xs text-destructive">
                  {errors.tuition_paid.message}
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="scholarship_amount">
                Scholarships / Grants Received ($)
              </Label>
              <Input
                id="scholarship_amount"
                type="number"
                min="0"
                step="0.01"
                placeholder="e.g. 8000"
                {...register("scholarship_amount", { valueAsNumber: true })}
              />
              <p className="text-xs text-muted-foreground">
                Total scholarships or grants received (1098-T Box 5).
              </p>
              {errors.scholarship_amount && (
                <p className="text-xs text-destructive">
                  {errors.scholarship_amount.message}
                </p>
              )}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="tuition_paid_to_nj">
              Was this tuition paid to a New Jersey institution?
            </Label>
            <select
              id="tuition_paid_to_nj"
              className="flex h-9 w-full max-w-xs rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]"
              {...register("tuition_paid_to_nj", {
                setValueAs: (v) => (v === "" ? undefined : v === "yes"),
              })}
              defaultValue=""
            >
              <option value="" disabled hidden>
                Select an option
              </option>
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="prior_years_aotc_claimed">
              How many prior tax years have you claimed the American Opportunity
              Tax Credit?
            </Label>
            <Input
              id="prior_years_aotc_claimed"
              type="number"
              min="0"
              max="4"
              placeholder="e.g. 0"
              {...register("prior_years_aotc_claimed", { valueAsNumber: true })}
            />
            <p className="text-xs text-muted-foreground">
              Leave blank if you&apos;re not sure. AOTC can only be claimed for 4 tax
              years total.
            </p>
            {errors.prior_years_aotc_claimed && (
              <p className="text-xs text-destructive">
                {errors.prior_years_aotc_claimed.message}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
