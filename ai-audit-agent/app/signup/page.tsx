"use client";

import { useActionState } from "react";
import Link from "next/link";
import { signup, type SignupState } from "./actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const LEDGER_STEPS = [
  { code: "01", label: "Residency status" },
  { code: "02", label: "Documents" },
  { code: "03", label: "Credits reviewed" },
  { code: "04", label: "Filing package" },
];

const initialState: SignupState = {};

export default function SignupPage() {
  const [state, formAction, isPending] = useActionState(signup, initialState);

  return (
    <div className="min-h-screen w-full grid lg:grid-cols-2 bg-[#F7F8FA]">
      <div className="hidden lg:flex flex-col justify-between bg-[#0F1C1A] text-[#EAF1EF] px-12 py-12">
        <div>
          <span className="font-mono text-xs tracking-[0.2em] text-[#7FA89E]">
            LEDGER
          </span>
        </div>

        <div className="max-w-sm">
          <h1 className="font-mono text-sm tracking-[0.15em] text-[#7FA89E] mb-4">
            CREATE ACCOUNT
          </h1>
          <p className="text-2xl leading-snug text-[#EAF1EF]">
            Know what&apos;s missing before you file.
          </p>
          <p className="mt-4 text-sm text-[#8FA39E] leading-relaxed">
            A few minutes of questions gets you a residency status, a document
            checklist, and the credits worth a closer look.
          </p>
        </div>

        <div className="border-t border-[#254038] pt-6">
          <ol className="space-y-3">
            {LEDGER_STEPS.map((step) => (
              <li key={step.code} className="flex items-center gap-3 text-sm">
                <span className="font-mono text-xs text-[#5C7C74]">
                  {step.code}
                </span>
                <span className="h-px flex-1 bg-[#254038]" />
                <span className="text-[#B9CBC6]">{step.label}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <span className="font-mono text-xs tracking-[0.2em] text-[#5C7C74]">
              LEDGER
            </span>
          </div>

          {state?.success ? (
            <div>
              <h2 className="text-xl font-medium text-[#12161C]">
                Account created
              </h2>
              <p className="mt-2 text-sm text-[#5B6470] leading-relaxed">
                {state.autoSignedIn
                  ? "Your account has been created and you're signed in."
                  : "Your account has been created successfully. Check your email to confirm your address before signing in."}
              </p>
              <Link
                href={state.autoSignedIn ? "/questionnaire" : "/login"}
                className="inline-block mt-6 text-sm text-[#1B6E67] hover:underline"
              >
                {state.autoSignedIn ? "Start the questionnaire" : "Continue to sign in"}
              </Link>
            </div>
          ) : (
            <>
              <h2 className="text-xl font-medium text-[#12161C]">
                Create your account
              </h2>
              <p className="mt-1 text-sm text-[#5B6470]">
                Takes a couple of minutes to get started.
              </p>

              <form action={formAction} className="mt-8 space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    placeholder="you@school.edu"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    name="password"
                    type="password"
                    autoComplete="new-password"
                    required
                    minLength={8}
                  />
                  <p className="text-xs text-[#8B93A0]">
                    At least 8 characters.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm password</Label>
                  <Input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    required
                    minLength={8}
                  />
                </div>

                {state?.error && (
                  <p
                    role="alert"
                    className="text-sm text-[#B3432F] bg-[#FBEAE6] border border-[#F0C7BC] rounded-md px-3 py-2"
                  >
                    {state.error}
                  </p>
                )}

                <Button
                  type="submit"
                  disabled={isPending}
                  className="w-full bg-[#1B6E67] hover:bg-[#16564F] text-white"
                >
                  {isPending ? "Creating account…" : "Create account"}
                </Button>
              </form>

              <p className="mt-6 text-sm text-[#5B6470]">
                Already have an account?{" "}
                <Link href="/login" className="text-[#1B6E67] hover:underline">
                  Sign in
                </Link>
              </p>

              <p className="mt-10 text-xs text-[#8B93A0] leading-relaxed">
                This tool audits documents and identifies missing information.
                It does not prepare or file tax returns, and does not provide
                legal or tax advice.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
