"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/utils/supabase/client";
import type { AuditSummary } from "./types";

export type AuditSummaryState =
  | { kind: "loading" }
  | { kind: "not_found" }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: AuditSummary };

/**for GET /audit/summary, shared by the Dashboard,
 * the Audit & Credit Discovery Hub and the Action Center. */
export function useAuditSummary(): AuditSummaryState {
  const [state, setState] = useState<AuditSummaryState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (!session) {
          if (!cancelled)
            setState({
              kind: "error",
              message: "Your session expired — please sign in again.",
            });
          return;
        }

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/audit/summary`,
          {
            headers: { Authorization: `Bearer ${session.access_token}` },
            cache: "no-store",
          },
        );

        if (cancelled) return;
        if (response.status === 404) return setState({ kind: "not_found" });
        if (!response.ok)
          return setState({
            kind: "error",
            message: "Could not load your results. Please try again.",
          });

        const data: AuditSummary = await response.json();
        setState({ kind: "ready", data });
      } catch {
        if (!cancelled)
          setState({
            kind: "error",
            message: "Could not reach the server. Check your connection.",
          });
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
