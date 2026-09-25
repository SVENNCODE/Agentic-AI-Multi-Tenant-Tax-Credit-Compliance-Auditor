import { NextResponse } from "next/server";
import { createClient } from "@/lib/utils/supabase/server";
import { safeRedirectPath } from "@/lib/utils/safe-redirect";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  // Only the same origin relative paths are honoured, default is the dashboard.
  const next = safeRedirectPath(searchParams.get("next"), "/dashboard");

  const redirectBase = process.env.NEXT_PUBLIC_SITE_URL || origin;

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      return NextResponse.redirect(new URL(next, redirectBase));
    }
  }

  return NextResponse.redirect(
    new URL("/login?error=auth_callback_failed", redirectBase),
  );
}
