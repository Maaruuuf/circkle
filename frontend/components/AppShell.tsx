"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth } from "./AuthContext";
import { Avatar } from "./Avatar";
import { Icon, type IconName } from "./Icon";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

interface NavLink {
  href: string;
  label: string;
  icon: IconName;
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, status, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  const links: NavLink[] = [
    { href: "/", label: "Home", icon: "home" },
    { href: "/explore", label: "Explore", icon: "compass" },
    { href: "/search", label: "Search", icon: "search" },
    ...(user ? [{ href: `/u/${user.username}`, label: "Profile", icon: "user" } as NavLink] : []),
    ...(user ? [{ href: "/settings", label: "Settings", icon: "settings" } as NavLink] : []),
    ...(user?.role === "admin" ? [{ href: "/admin", label: "Admin", icon: "shield" } as NavLink] : []),
  ];

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <div className="min-h-screen md:flex">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-line p-5 md:flex">
        <Logo className="mb-8" />
        <nav aria-label="Main" className="space-y-1">
          {links.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-3 rounded-full px-4 py-2.5 text-sm font-medium transition ${
                  active ? "bg-ink text-canvas" : "text-ink hover:bg-surface2"
                }`}
              >
                <Icon name={link.icon} className="h-[18px] w-[18px]" />
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto space-y-4 border-t border-line pt-4">
          {status === "authenticated" && user ? (
            <>
              <Link href={`/u/${user.username}`} className="flex items-center gap-3 rounded-xl p-1 hover:bg-surface2">
                <Avatar name={user.display_name} src={user.avatar_url} size="sm" />
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold">{user.display_name}</span>
                  <span className="block truncate text-xs text-muted">@{user.username}</span>
                </span>
              </Link>
              <div className="flex items-center justify-between">
                <button
                  onClick={handleLogout}
                  className="inline-flex items-center gap-2 text-sm font-medium text-muted hover:text-danger"
                >
                  <Icon name="logout" className="h-4 w-4" />
                  Log out
                </button>
                <ThemeToggle />
              </div>
            </>
          ) : (
            <div className="flex items-center justify-between">
              <div className="space-x-4 text-sm font-semibold">
                <Link href="/login" className="text-brand">Log in</Link>
                <Link href="/register">Sign up</Link>
              </div>
              <ThemeToggle />
            </div>
          )}
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        {/* Mobile top bar */}
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-canvas/90 px-4 py-3 backdrop-blur md:hidden">
          <Logo />
          <ThemeToggle />
        </header>
        <main className="mx-auto w-full max-w-xl px-3 pb-28 pt-5 md:pb-10">{children}</main>
      </div>

      {/* Mobile bottom bar */}
      <nav
        aria-label="Main"
        className="fixed inset-x-3 bottom-3 z-10 flex justify-around rounded-full border border-line bg-surface/95 p-1.5 shadow-float backdrop-blur md:hidden"
      >
        {links.slice(0, 5).map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              aria-label={link.label}
              aria-current={active ? "page" : undefined}
              className={`rounded-full p-2.5 ${active ? "bg-ink text-canvas" : "text-ink"}`}
            >
              <Icon name={link.icon} />
            </Link>
          );
        })}
        {status === "anonymous" && (
          <Link href="/login" className="rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white">
            Log in
          </Link>
        )}
      </nav>
    </div>
  );
}
