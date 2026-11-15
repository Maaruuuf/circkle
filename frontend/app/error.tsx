"use client";

import { primaryButton } from "@/lib/ui";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="mx-auto max-w-md p-12 text-center">
      <h1 className="text-2xl font-bold">Something went wrong</h1>
      <p className="mt-2 text-muted">An unexpected error happened. Please try again.</p>
      <button onClick={reset} className={`${primaryButton} mt-6`}>
        Try again
      </button>
    </div>
  );
}
