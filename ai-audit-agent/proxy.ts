import { type NextRequest } from "next/server";
import { updateSession } from "@/lib/utils/supabase/session";

// Next.js 16 "Proxy" (formerly Middleware). Must live at the project root —
// the previous lib/utils/supabase/middleware.ts was never executed.
export async function proxy(request: NextRequest) {
  return await updateSession(request);
}

export const config = {
  matcher: [
    /*
     * Match all request paths except static assets:
     * _next/static, _next/image, favicon.ico and image files.
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
