/**
 * Returns `next` only if it is a same-origin relative path; otherwise the
 * fallback. Blocks open redirects such as "//evil.com", "/\\evil.com",
 * "@evil.com", ".evil.com" or "https://evil.com".
 */
export function safeRedirectPath(
  next: string | null | undefined,
  fallback = "/dashboard",
): string {
  if (!next || typeof next !== "string") return fallback;
  if (next.length > 512) return fallback;
  if (!next.startsWith("/")) return fallback;
  if (next.startsWith("//") || next.startsWith("/\\")) return fallback;
  // Reject control characters and backslashes anywhere.
  if (/[\u0000-\u001f\u007f\\]/.test(next)) return fallback;
  try {
    const url = new URL(next, "http://placeholder.invalid");
    if (url.origin !== "http://placeholder.invalid") return fallback;
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return fallback;
  }
}
