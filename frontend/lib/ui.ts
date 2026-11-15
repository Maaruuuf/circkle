// Shared Tailwind class strings, so forms and buttons look the same everywhere.
export const inputClass =
  "w-full rounded-xl border border-line bg-surface px-3.5 py-2.5 text-sm text-ink placeholder:text-muted/70 outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20 disabled:bg-surface2";

const pill =
  "inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 disabled:cursor-not-allowed disabled:opacity-50";

/** Main call to action (orange). */
export const primaryButton = `${pill} bg-brand text-white hover:brightness-110 active:brightness-95`;
/** Strong neutral button (black in light mode, cream in dark mode). */
export const inkButton = `${pill} bg-ink text-canvas hover:opacity-90`;
export const secondaryButton = `${pill} border border-line bg-surface text-ink hover:bg-surface2`;
export const dangerButton = `${pill} bg-danger text-white hover:brightness-110`;

export const cardClass = "rounded-2xl border border-line bg-surface";
