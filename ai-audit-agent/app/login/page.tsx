"use client";

import { useActionState, useState } from "react";
import Link from "next/link";
import { login, resendConfirmation, type LoginState } from "./action";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const LEDGER_STEPS = [
  { code: "01", label: "Residency status" },
  { code: "02", label: "Documents" },
  { code: "03", label: "Credits reviewed" },
  { code: "04", label: "Filing package" },
];

const initialState: LoginState = {};

export default function LoginPage() {
  const [state, formAction, isPending] = useActionState(login, initialState);
  const [resendStatus, setResendStatus] = useState<
    "idle" | "sending" | "sent" | "error"
  >("idle");

  async function handleResend() {
    if (!state.email) return;
    setResendStatus("sending");
    const result = await resendConfirmation(state.email);
    setResendStatus(result.error ? "error" : "sent");
  }

  return (
    <div className="min-h-screen w-full grid lg:grid-cols-2 bg-[#F7F8FA]">
      {/* Brand / context panel */}
      <div className="hidden lg:flex flex-col justify-between bg-[#0F1C1A] text-[#EAF1EF] px-12 py-12">
        <div>
          <span className="font-mono text-xs tracking-[0.2em] text-[#7FA89E]">
            LEDGER
          </span>
        </div>

        <div className="max-w-sm">
          <h1 className="font-mono text-sm tracking-[0.15em] text-[#7FA89E] mb-4">
            SIGN IN
          </h1>
          <p className="text-2xl leading-snug text-[#EAF1EF]">
            Every filing starts with knowing where you stand.
          </p>
          <p className="mt-4 text-sm text-[#8FA39E] leading-relaxed">
            This application check residency status, missing documents, and
            applicable credits before anything else runs in the same order,
            every time.
          </p>
        </div>

        {/* Signature element */}
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

          <h2 className="text-xl font-medium text-[#12161C]">Sign in</h2>
          <p className="mt-1 text-sm text-[#5B6470]">
            Use the email and password from your account.
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
                autoComplete="current-password"
                required
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

            {state?.needsConfirmation && (
              <div
                role="alert"
                className="text-sm bg-[#FBF3E6] border border-[#F0DEBC] rounded-md px-3 py-2 space-y-2"
              >
                <p className="text-[#8A5A1F]">
                  Your email hasn&apos;t been confirmed yet. Check your inbox
                  for the confirmation link.
                </p>
                {resendStatus === "sent" ? (
                  <p className="text-[#1B6E67]">
                    Sent, check your inbox/spam for a new link.
                  </p>
                ) : (
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={resendStatus === "sending"}
                    className="text-[#1B6E67] hover:underline font-medium"
                  >
                    {resendStatus === "sending"
                      ? "Sending…"
                      : "Resend confirmation email"}
                  </button>
                )}
                {resendStatus === "error" && (
                  <p className="text-[#B3432F]">
                    Couldn&apos;t resend, try again shortly.
                  </p>
                )}
              </div>
            )}

            <Button
              type="submit"
              disabled={isPending}
              className="w-full bg-[#1B6E67] hover:bg-[#16564F] text-white"
            >
              {isPending ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <p className="mt-6 text-sm text-[#5B6470]">
            Don&apos;t have an account?{" "}
            <Link href="/signup" className="text-[#1B6E67] hover:underline">
              Create one
            </Link>
          </p>

          <p className="mt-10 text-xs text-[#8B93A0] leading-relaxed">
            This tool audits documents and identifies missing information. It
            does not prepare or file tax returns, and does not provide legal or
            tax advice.
          </p>
        </div>
      </div>
    </div>
  );
}
