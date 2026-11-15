/**
 * Only allow redirects to paths inside our own app. Blocks open-redirect attacks such as
 * /login?next=https://evil.com or /login?next=//evil.com
 */
export function safeNextPath(next: string | null | undefined, fallback = "/"): string {
  if (!next) return fallback;
  if (!next.startsWith("/") || next.startsWith("//") || next.includes("\\")) return fallback;
  return next;
}
