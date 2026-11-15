"use client";

import type { ReactNode } from "react";
import { AppShell } from "./AppShell";
import { useAuth } from "./AuthContext";
import { Feed } from "./Feed";

/**
 * `/` shows the feed to logged-in users and the marketing page to everyone else.
 * The landing page is rendered on the server (good for search engines and link previews)
 * and passed in as a prop; the browser swaps to the feed once it knows you are logged in.
 */
export function HomeGate({ landing }: { landing: ReactNode }) {
  const { status } = useAuth();
  if (status === "authenticated") {
    return (
      <AppShell>
        <Feed />
      </AppShell>
    );
  }
  return <>{landing}</>;
}
