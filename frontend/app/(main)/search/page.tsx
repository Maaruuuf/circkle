"use client";

import { useEffect, useState } from "react";
import { ErrorText } from "@/components/ErrorText";
import { UserRow } from "@/components/UserRow";
import { errorMessage, usersApi } from "@/lib/api";
import type { UserSummary } from "@/lib/types";
import { inputClass } from "@/lib/ui";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<UserSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const term = query.trim();
    if (term.length < 2) {
      setResults([]);
      return;
    }
    // Debounce: wait until the user pauses typing before calling the API.
    const timer = setTimeout(() => {
      usersApi
        .search(term)
        .then((found) => {
          setResults(found);
          setError(null);
        })
        .catch((caught) => setError(errorMessage(caught)));
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  return (
    <>
      <h1 className="mb-4 text-xl font-bold">Search people</h1>
      <input
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search by username or name"
        aria-label="Search people"
        className={inputClass}
      />
      <div className="mt-4 space-y-3">
        <ErrorText message={error} />
        <ul className="rounded-2xl border border-line bg-surface p-2 empty:hidden">
          {results.map((user) => (
            <UserRow key={user.id} user={user} />
          ))}
        </ul>
        {query.trim().length >= 2 && results.length === 0 && !error && (
          <p className="text-center text-sm text-muted">No people found.</p>
        )}
      </div>
    </>
  );
}
