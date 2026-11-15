import type { ReactNode } from "react";
import { Logo } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center px-4 py-10">
      <ThemeToggle className="absolute right-4 top-4" />
      <Logo className="mb-6 scale-110" />
      <div className="w-full max-w-sm space-y-4 rounded-3xl border border-line bg-surface p-7 shadow-float">
        {children}
      </div>
    </div>
  );
}
