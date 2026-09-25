import { z } from "zod";

// Mirrors the Postgres enums so invalid values never reach FastAPI.
export const visaTypeEnum = z.enum([
  "F1",
  "J1",
  "M1",
  "Q1",
  "H1B",
  "OPT",
  "OTHER",
  "NONE",
]);

export const filingStatusEnum = z.enum([
  "SINGLE",
  "MARRIED_FILING_JOINTLY",
  "MARRIED_FILING_SEPARATELY",
  "HEAD_OF_HOUSEHOLD",
  "QUALIFYING_SURVIVING_SPOUSE",
]);

export const employmentTypeEnum = z.enum([
  "W2",
  "CONTRACTOR_1099",
  "UNEMPLOYED",
  "STUDENT_WORKER",
]);

const visaPeriodSchema = z
  .object({
    visa_type: visaTypeEnum,
    start_date: z.string().min(1, "Start date is required"),
    end_date: z.string().optional(),
    is_exempt_status: z.boolean(),
  })
  .refine(
    (period) => !period.end_date || period.end_date >= period.start_date,
    { message: "End date must be after start date", path: ["end_date"] },
  );

// --- Step 1: Profile & immigration -----------------------------------
export const profileStepSchema = z.object({
  state_of_residence: z
    .string()
    .regex(/^[A-Za-z]{2}$/, "Use a 2-letter state code")
    .transform((v) => v.toUpperCase()),
  filing_status: filingStatusEnum,
  citizenship_country: z
    .string()
    .regex(/^[A-Za-z]{3}$/, "Use the 3-letter country code (e.g. IND, CHN)")
    .transform((v) => v.toUpperCase()),
  us_entry_date: z.string().min(1, "Entry date is required"),
  current_visa_type: visaTypeEnum,
  is_fulltime_student: z.boolean(),
  employment_type: employmentTypeEnum,
  spouse_is_us_citizen_or_resident: z.boolean().optional(),

  // Tax ID compliance: a boolean only. No SSN digits are collected or sent
  has_valid_ssn: z.boolean({
    required_error: "Please select whether you hold a valid SSN",
  }),

  visa_status_periods: z
    .array(visaPeriodSchema)
    .min(1, "Add at least your current visa status")
    .max(20, "At most 20 visa periods"),
});

// --- Step 2: Income summary & Physical Presence -----------------------
export const incomeStepSchema = z.object({
  // Physical Presence Days (Coerced from HTML string input to number)
  days_present_current_year: z.coerce
    .number({ invalid_type_error: "Must be a valid number" })
    .min(0, "Days cannot be negative")
    .max(366, "Days cannot exceed 366")
    .default(0),
  days_present_prior_year: z.coerce
    .number({ invalid_type_error: "Must be a valid number" })
    .min(0, "Days cannot be negative")
    .max(366, "Days cannot exceed 366")
    .default(0),
  days_present_two_years_prior: z.coerce
    .number({ invalid_type_error: "Must be a valid number" })
    .min(0, "Days cannot be negative")
    .max(366, "Days cannot exceed 366")
    .default(0),

  // Income Fields
  annual_income: z.coerce
    .number()
    .min(0, "Enter a value of 0 or more")
    .max(100_000_000),
  number_of_employers: z.coerce
    .number()
    .int()
    .min(0, "Enter a value of 0 or more")
    .max(50),
  scholarship_amount: z.coerce
    .number()
    .min(0, "Enter a value of 0 or more")
    .max(100_000_000),
  tuition_paid: z.coerce
    .number()
    .min(0, "Enter a value of 0 or more")
    .max(100_000_000),
  tuition_paid_to_nj: z.boolean().optional(),
});

// --- Step 3: Expense categories ----------------------------------------
export const expensesStepSchema = z.object({
  has_education_expenses: z.boolean(),
  has_childcare_expenses: z.boolean(),
  has_medical_expenses: z.boolean(),
  has_charitable_donations: z.boolean(),
  has_retirement_contributions: z.boolean(),

  // Education Credit Lifetime Limit Tracking (AOTC 4-year limit)
  prior_years_aotc_claimed: z.coerce
    .number()
    .int()
    .min(0, "Cannot be less than 0")
    .max(4, "AOTC maximum is 4 years")
    .optional(),
});

// --- Complete Form Schema ----------------------------------------------
export const questionnaireSchema = profileStepSchema
  .merge(incomeStepSchema)
  .merge(expensesStepSchema)
  .extend({
    tax_year: z.number().default(2025),
  });

export type QuestionnaireInput = z.input<typeof questionnaireSchema>;
export type QuestionnaireOutput = z.output<typeof questionnaireSchema>;
export type VisaPeriodInput = z.input<typeof visaPeriodSchema>;
