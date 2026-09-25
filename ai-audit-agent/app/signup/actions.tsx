"use server";

import { createClient } from "@/lib/utils/supabase/server";

export type SignupState = {
  error?: string;
  success?: boolean;
  // True when Supabase returned an active session immediately (email
  // confirmation disabled on the project). False/undefined means the
  // account still needs to confirm its email before signing in.
  autoSignedIn?: boolean;
};

export async function signup(
  _prevState: SignupState,
  formData: FormData,
): Promise<SignupState> {
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;
  const confirmPassword = formData.get("confirmPassword") as string;

  if (!email || !password) {
    return { error: "Enter your email and a password to continue." };
  }

  if (email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return { error: "Enter a valid email address." };
  }

  if (password.length > 128) {
    return { error: "Password must be 128 characters or fewer." };
  }

  if (
    password.length < 8 ||
    !/[A-Za-z]/.test(password) ||
    !/\d/.test(password)
  ) {
    return {
      error:
        "Password must be at least 8 characters and include letters and numbers.",
    };
  }

  if (password !== confirmPassword) {
    return { error: "Passwords don’t match." };
  }

  const supabase = await createClient();
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
  });

  if (error) {
    const message = error.message.toLowerCase();
    if (message.includes("password")) {
      return {
        error:
          "Password does not meet the requirements (at least 8 characters, letters and numbers).",
      };
    }
    if (message.includes("already registered")) {
      return {
        error: "An account with this email address already exists.",
      };
    }
    return {
      error: "Something went wrong creating your account. Please try again.",
    };
  }

  return { success: true, autoSignedIn: !!data.session };
}
