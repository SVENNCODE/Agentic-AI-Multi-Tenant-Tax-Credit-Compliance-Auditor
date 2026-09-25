"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { createClient } from "@/lib/utils/supabase/client";

// Order matters: this is the intended user journey through the app.
const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/questionnaire", label: "Questionnaire" },
  { href: "/audit", label: "Credit Hub" },
  { href: "/action-center", label: "Action Center" },
] as const;

export function AppNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace("/login");
    router.refresh();
  }

  return (
    <header className="bg-white border-b border-[#E3E6EA] px-6 py-4">
      <div className="max-w-3xl mx-auto flex flex-wrap items-center justify-between gap-3">
        <Link href="/dashboard" className="text-sm font-medium text-[#12161C]">
          Tax Auditor
        </Link>
        <nav
          aria-label="Main"
          className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm"
        >
          {NAV_LINKS.map(({ href, label }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={
                  active
                    ? "text-[#12161C] font-medium"
                    : "text-[#5B6470] hover:text-[#12161C] transition-colors"
                }
              >
                {label}
              </Link>
            );
          })}
          <button
            type="button"
            onClick={handleSignOut}
            disabled={signingOut}
            className="text-[#5B6470] hover:text-[#12161C] transition-colors disabled:opacity-50"
          >
            {signingOut ? "Signing out…" : "Sign out"}
          </button>
        </nav>
      </div>
    </header>
  );
}
