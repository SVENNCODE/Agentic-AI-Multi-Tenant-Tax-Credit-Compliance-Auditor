"use client";

import { useFormContext, useFieldArray, Controller } from "react-hook-form";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import type { QuestionnaireInput } from "@/lib/utils/validation/questionnaire";

const VISA_TYPES = [
  "F1",
  "J1",
  "M1",
  "H1B",
  "OPT",
  "OTHER",
  "NONE",
  "Q1",
] as const;
const FILING_STATUSES = [
  "SINGLE",
  "MARRIED_FILING_JOINTLY",
  "MARRIED_FILING_SEPARATELY",
  "HEAD_OF_HOUSEHOLD",
  "QUALIFYING_SURVIVING_SPOUSE",
] as const;
const EMPLOYMENT_TYPES = [
  "W2",
  "CONTRACTOR_1099",
  "UNEMPLOYED",
  "STUDENT_WORKER",
] as const;

export function ProfileStep() {
  const {
    register,
    control,
    watch,
    formState: { errors },
  } = useFormContext<QuestionnaireInput>();

  const { fields, append, remove } = useFieldArray({
    control,
    name: "visa_status_periods",
  });

  const filingStatus = watch("filing_status");

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-sm font-medium text-[#12161C] mb-4">Profile</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="state_of_residence">State of residence</Label>
            <Input
              id="state_of_residence"
              placeholder="NJ"
              maxLength={2}
              {...register("state_of_residence")}
            />
            {errors.state_of_residence && (
              <p className="text-xs text-[#B3432F]">
                {errors.state_of_residence.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="filing_status">Filing status</Label>
            <select
              id="filing_status"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]"
              {...register("filing_status")}
            >
              {FILING_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="citizenship_country">Country of citizenship</Label>
            <Input
              id="citizenship_country"
              placeholder="IND"
              maxLength={3}
              {...register("citizenship_country")}
            />
            <p className="text-xs text-[#8B93A0]">
              3 letter code used to check tax treaty eligibility.
            </p>
            {errors.citizenship_country && (
              <p className="text-xs text-[#B3432F]">
                {errors.citizenship_country.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="us_entry_date">
              Initial U.S. entry date (F/J/M status)
            </Label>
            <Input
              id="us_entry_date"
              type="date"
              {...register("us_entry_date")}
            />
            {errors.us_entry_date && (
              <p className="text-xs text-[#B3432F]">
                {errors.us_entry_date.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="current_visa_type">Current visa status</Label>
            <select
              id="current_visa_type"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]"
              {...register("current_visa_type")}
            >
              {VISA_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="employment_type">Employment type</Label>
            <select
              id="employment_type"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]"
              {...register("employment_type")}
            >
              {EMPLOYMENT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2 mt-4">
          <Controller
            control={control}
            name="is_fulltime_student"
            render={({ field }) => (
              <Checkbox
                id="is_fulltime_student"
                checked={field.value}
                onCheckedChange={field.onChange}
              />
            )}
          />
          <Label htmlFor="is_fulltime_student" className="font-normal">
            I am a full-time student
          </Label>
        </div>

        <div className="space-y-2 mt-4">
          <Label htmlFor="has_valid_ssn">
            Do you have a Social Security Number issued for work purposes?
          </Label>
          <select
            id="has_valid_ssn"
            className="flex h-9 w-full max-w-xs rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]"
            {...register("has_valid_ssn", {
              setValueAs: (v) => (v === "" ? undefined : v === "yes"),
            })}
            defaultValue=""
          >
            <option value="">Not sure</option>
            <option value="yes">Yes</option>
            <option value="no">
              No, I use an ITIN, or don&apos;t have one
            </option>
          </select>
        </div>

        {(filingStatus === "MARRIED_FILING_JOINTLY" ||
          filingStatus === "MARRIED_FILING_SEPARATELY") && (
          <div className="flex items-center gap-2 mt-3">
            <Controller
              control={control}
              name="spouse_is_us_citizen_or_resident"
              render={({ field }) => (
                <Checkbox
                  id="spouse_is_us_citizen_or_resident"
                  checked={field.value ?? false}
                  onCheckedChange={field.onChange}
                />
              )}
            />
            <Label
              htmlFor="spouse_is_us_citizen_or_resident"
              className="font-normal"
            >
              My spouse is a U.S. citizen or resident
            </Label>
          </div>
        )}
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-[#12161C]">
            Visa status history
          </h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              append({
                visa_type: "F1",
                start_date: "",
                end_date: "",
                is_exempt_status: true,
              })
            }
          >
            Add period
          </Button>
        </div>
        <p className="text-xs text-[#8B93A0] mb-4">
          List every F, J, M, or Q status period you&apos;ve held, this
          determines how many exempt years you have left under the Substantial
          Presence Test.
        </p>

        <div className="space-y-4">
          {fields.map((field, index) => (
            <div
              key={field.id}
              className="grid grid-cols-[1fr_1fr_1fr_auto_auto] gap-3 items-end border border-[#E3E6EA] rounded-md p-3"
            >
              <div className="space-y-1.5">
                <Label className="text-xs">Visa type</Label>
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-2 text-sm shadow-xs outline-none"
                  {...register(
                    `visa_status_periods.${index}.visa_type` as const,
                  )}
                >
                  {VISA_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Start date</Label>
                <Input
                  type="date"
                  {...register(
                    `visa_status_periods.${index}.start_date` as const,
                  )}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">End date (blank = ongoing)</Label>
                <Input
                  type="date"
                  {...register(
                    `visa_status_periods.${index}.end_date` as const,
                  )}
                />
              </div>
              <div className="flex items-center gap-2 pb-2">
                <Controller
                  control={control}
                  name={
                    `visa_status_periods.${index}.is_exempt_status` as const
                  }
                  render={({ field: checkboxField }) => (
                    <Checkbox
                      id={`visa_status_periods.${index}.is_exempt_status`}
                      checked={checkboxField.value}
                      onCheckedChange={checkboxField.onChange}
                    />
                  )}
                />
                <Label
                  htmlFor={`visa_status_periods.${index}.is_exempt_status`}
                  className="text-xs font-normal"
                >
                  Exempt (F/J/M/Q)
                </Label>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => remove(index)}
                disabled={fields.length === 1}
              >
                Remove
              </Button>
            </div>
          ))}
        </div>
        {errors.visa_status_periods?.message && (
          <p className="text-xs text-[#B3432F] mt-2">
            {errors.visa_status_periods.message as string}
          </p>
        )}
      </div>
    </div>
  );
}
