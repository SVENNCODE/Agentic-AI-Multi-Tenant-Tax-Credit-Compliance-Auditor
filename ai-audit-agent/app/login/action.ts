"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/utils/supabase/server";

export type LoginState = {
  error?: string;
  needsConfirmation?: boolean;
  email?: string;
};

export async function login(
  _prevState: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;

  if (!email || !password) {
    return { error: "Enter your email and password to continue." };
  }

  const supabase = await createClient();

  const { error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });
  // Error message is vague on purpose
  if (error) {
    if (error.message.toLowerCase().includes("email not confirmed")) {
      return { needsConfirmation: true, email };
    }
    return { error: "Incorrect email or password." };
  }

  redirect("/dashboard");
}

export type ResendState = {
  sent?: boolean;
  error?: string;
};

export async function resendConfirmation(email: string): Promise<ResendState> {
  if (
    typeof email !== "string" ||
    email.length > 254 ||
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  ) {
    return { error: "Missing or invalid email address." };
  }

  const supabase = await createClient();

  // Note for me :Supabase Auth applies its own per-address/per-IP email rate limits
  // (Dashboard -> Authentication -> Rate Limits).
  const { error } = await supabase.auth.resend({
    type: "signup",
    email,
    options: {
      emailRedirectTo: `${process.env.NEXT_PUBLIC_SITE_URL}/auth/callback`,
    },
  });

  if (error && error.status === 429) {
    return { error: "Too many requests. Please wait a minute and try again." };
  }

  return { sent: true };
}
