"use client";

import { useFormContext } from "react-hook-form";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { QuestionnaireInput } from "@/lib/utils/validation/questionnaire";

export function IncomeStep() {
  const {
    register,
    watch,
    formState: { errors },
  } = useFormContext<QuestionnaireInput>();

  const taxYear = watch("tax_year") || 2025;

  return (
    <div className="space-y-6">
      {/* Physical Presence Section */}
      <div className="space-y-4">
        <div>
          <h3 className="text-sm font-medium text-[#12161C] mb-1">
            Physical presence in the U.S.
          </h3>
          <p className="text-sm text-muted-foreground">
            Enter the exact or estimated number of days you were physically
            present in the U.S. for each year.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Current Tax Year */}
          <div className="space-y-2">
            <Label htmlFor="days_present_current_year">
              Days in {taxYear} (Current)
            </Label>
            <Input
              id="days_present_current_year"
              type="number"
              min={0}
              max={366}
              placeholder="e.g. 180"
              {...register("days_present_current_year")}
            />
            {errors.days_present_current_year && (
              <p className="text-xs text-[#B3432F]">
                {errors.days_present_current_year.message}
              </p>
            )}
          </div>

          {/* Prior Year 1 */}
          <div className="space-y-2">
            <Label htmlFor="days_present_prior_year">
              Days in {taxYear - 1}
            </Label>
            <Input
              id="days_present_prior_year"
              type="number"
              min={0}
              max={366}
              placeholder="e.g. 365"
              {...register("days_present_prior_year")}
            />
            {errors.days_present_prior_year && (
              <p className="text-xs text-[#B3432F]">
                {errors.days_present_prior_year.message}
              </p>
            )}
          </div>

          {/* Prior Year 2 */}
          <div className="space-y-2">
            <Label htmlFor="days_present_two_years_prior">
              Days in {taxYear - 2}
            </Label>
            <Input
              id="days_present_two_years_prior"
              type="number"
              min={0}
              max={366}
              placeholder="e.g. 365"
              {...register("days_present_two_years_prior")}
            />
            {errors.days_present_two_years_prior && (
              <p className="text-xs text-[#B3432F]">
                {errors.days_present_two_years_prior.message}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Income Section */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-[#12161C]">Income summary</h3>

        <div className="grid grid-cols-2 gap-4">
          {/* Annual Income */}
          <div className="space-y-2">
            <Label htmlFor="annual_income">Annual income ($)</Label>
            <Input
              id="annual_income"
              type="number"
              step="0.01"
              min={0}
              {...register("annual_income", { valueAsNumber: true })}
            />
            {errors.annual_income && (
              <p className="text-xs text-[#B3432F]">
                {errors.annual_income.message}
              </p>
            )}
          </div>

          {/* Number of Employers */}
          <div className="space-y-2">
            <Label htmlFor="number_of_employers">Number of employers</Label>
            <Input
              id="number_of_employers"
              type="number"
              min={0}
              {...register("number_of_employers", { valueAsNumber: true })}
            />
            {errors.number_of_employers && (
              <p className="text-xs text-[#B3432F]">
                {errors.number_of_employers.message}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
