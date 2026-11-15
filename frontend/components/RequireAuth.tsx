"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "./AuthContext";
import { Spinner } from "./Spinner";

/**
 * Client-side route guard: sends guests to /login. This is for UX only.
 * The real protection is the backend, which checks the cookie on every request.
 */
export function RequireAuth({ children, admin = false }: { children: ReactNode; admin?: boolean }) {
  const { user, status } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "anonymous") router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [status, router, pathname]);

  if (status === "loading" || status === "anonymous") return <Spinner />;
  if (admin && user?.role !== "admin") {
    return <p className="p-8 text-center text-muted">You do not have access to this page.</p>;
  }
  return <>{children}</>;
}
