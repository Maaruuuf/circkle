"use client";

import { Icon } from "./Icon";

/** Light/dark switch. The choice is saved in localStorage; the inline script in layout.tsx reads it on load. */
export function ThemeToggle({ className = "" }: { className?: string }) {
  const toggle = () => {
    const isDark = document.documentElement.classList.toggle("dark");
    try {
      localStorage.setItem("theme", isDark ? "dark" : "light");
    } catch {
      /* storage blocked (private mode): the choice just lasts until reload */
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label="Toggle dark mode"
      title="Toggle dark mode"
      className={`inline-flex h-9 w-9 items-center justify-center rounded-full border border-line bg-surface text-ink transition hover:bg-surface2 ${className}`}
    >
      <Icon name="moon" className="h-4 w-4 dark:hidden" />
      <Icon name="sun" className="hidden h-4 w-4 dark:block" />
    </button>
  );
}
