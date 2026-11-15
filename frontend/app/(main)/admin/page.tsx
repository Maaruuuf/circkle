"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthContext";
import { ErrorText } from "@/components/ErrorText";
import { RequireAuth } from "@/components/RequireAuth";
import { Spinner } from "@/components/Spinner";
import { adminApi, errorMessage } from "@/lib/api";
import type { AdminStats, AdminUser } from "@/lib/types";
import { cardClass, secondaryButton } from "@/lib/ui";
import { usePaginated } from "@/lib/usePaginated";

function AdminContent() {
  const { user: me } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const users = usePaginated<AdminUser>((cursor) => adminApi.users(cursor), "admin-users");

  useEffect(() => {
    adminApi.stats().then(setStats).catch((caught) => setError(errorMessage(caught)));
  }, []);

  const update = async (target: AdminUser, change: { is_active?: boolean; role?: "user" | "admin" }) => {
    setError(null);
    try {
      const updated = await adminApi.updateUser(target.id, change);
      users.setItems((previous) => previous.map((u) => (u.id === updated.id ? updated : u)));
    } catch (caught) {
      setError(errorMessage(caught));
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Admin</h1>
      <ErrorText message={error} />
      {stats && (
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {Object.entries(stats).map(([label, value]) => (
            <div key={label} className={`${cardClass} p-3 text-center`}>
              <dd className="text-lg font-bold">{value}</dd>
              <dt className="text-xs capitalize text-muted">{label.replace("_", " ")}</dt>
            </div>
          ))}
        </dl>
      )}
      <ul className="space-y-2">
        {users.items.map((u) => (
          <li key={u.id} className={`${cardClass} flex flex-wrap items-center justify-between gap-2 p-3`}>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">
                @{u.username} {u.role === "admin" && <span className="text-xs text-brand">admin</span>}
                {!u.is_active && <span className="ml-1 text-xs text-danger">banned</span>}
              </p>
              <p className="truncate text-xs text-muted">{u.email}</p>
            </div>
            {u.id !== me?.id && (
              <div className="flex gap-2">
                <button className={secondaryButton} onClick={() => update(u, { is_active: !u.is_active })}>
                  {u.is_active ? "Ban" : "Unban"}
                </button>
                <button className={secondaryButton} onClick={() => update(u, { role: u.role === "admin" ? "user" : "admin" })}>
                  {u.role === "admin" ? "Remove admin" : "Make admin"}
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
      {users.loading && <Spinner />}
      {!users.loading && users.hasMore && (
        <button className={secondaryButton} onClick={() => users.loadMore()}>Load more</button>
      )}
    </div>
  );
}

export default function AdminPage() {
  return (
    <RequireAuth admin>
      <AdminContent />
    </RequireAuth>
  );
}
