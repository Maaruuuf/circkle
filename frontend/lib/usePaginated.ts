"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "./api";
import type { Page } from "./types";

/** Cursor-paginated list with "load more". `resetKey` restarts the list when it changes. */
export function usePaginated<T>(fetchPage: (cursor: string | null) => Promise<Page<T>>, resetKey: string) {
  const [items, setItems] = useState<T[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fetchRef = useRef(fetchPage);
  fetchRef.current = fetchPage;
  const generation = useRef(0);

  const load = useCallback(async (cursor: string | null, replace: boolean) => {
    const current = ++generation.current;
    setLoading(true);
    setError(null);
    try {
      const page = await fetchRef.current(cursor);
      if (current !== generation.current) return; // a newer request replaced this one
      setItems((previous) => (replace ? page.items : [...previous, ...page.items]));
      setNextCursor(page.next_cursor);
    } catch (caught) {
      if (current === generation.current) setError(errorMessage(caught));
    } finally {
      if (current === generation.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(null, true);
  }, [resetKey, load]);

  return {
    items,
    setItems,
    loading,
    error,
    hasMore: nextCursor !== null,
    loadMore: () => load(nextCursor, false),
    reload: () => load(null, true),
  };
}
