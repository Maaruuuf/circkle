import type { PublicProfile } from "./types";

// Server Components run on the web host (Vercel), so they call the backend directly.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8001";

export type ProfileResult =
  | { status: "ok"; profile: PublicProfile }
  | { status: "missing" } // the backend says this user does not exist
  | { status: "unavailable" }; // backend asleep / slow / down: do NOT claim "not found"

/** Public profile for server-side rendering (SEO + fast first paint). No cookies are forwarded. */
export async function fetchProfileServer(username: string): Promise<ProfileResult> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/users/${encodeURIComponent(username)}`, {
      next: { revalidate: 30 },
      signal: AbortSignal.timeout(8000),
    });
    if (response.status === 404) return { status: "missing" };
    if (!response.ok) return { status: "unavailable" };
    return { status: "ok", profile: (await response.json()) as PublicProfile };
  } catch {
    return { status: "unavailable" };
  }
}
