"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { ApiError, authApi } from "@/lib/api";
import type { Me } from "@/lib/types";

type Status = "loading" | "authenticated" | "anonymous";

interface AuthValue {
  user: Me | null;
  status: Status;
  setUser: (user: Me | null) => void;
  login: (email: string, password: string) => Promise<Me>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<Me | null>(null);
  const [status, setStatus] = useState<Status>("loading");

  const setUser = useCallback((next: Me | null) => {
    setUserState(next);
    setStatus(next ? "authenticated" : "anonymous");
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      setUser(await authApi.me());
    } catch (error) {
      // 401 just means "not logged in". Anything else (network, 5xx) should not look like a logout bug.
      if (!(error instanceof ApiError) || error.status !== 401) console.error(error);
      setUser(null);
    }
  }, [setUser]);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      const me = await authApi.login({ email, password });
      setUser(me);
      return me;
    },
    [setUser],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
    }
  }, [setUser]);

  const value = useMemo(
    () => ({ user, status, setUser, login, logout, refreshUser }),
    [user, status, setUser, login, logout, refreshUser],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
