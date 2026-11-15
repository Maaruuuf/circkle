import Link from "next/link";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <Link href="/" className={`inline-flex items-center gap-2.5 ${className}`} aria-label="Circkle home">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-ink text-canvas" aria-hidden="true">
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round">
          <path d="M18 7.5A7.5 7.5 0 1 0 18 16.5" />
        </svg>
      </span>
      <span className="text-lg font-bold tracking-tight">Circkle</span>
    </Link>
  );
}
