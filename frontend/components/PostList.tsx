"use client";

import type { ReactNode } from "react";
import type { Page, Post } from "@/lib/types";
import { usePaginated } from "@/lib/usePaginated";
import { PostCard } from "./PostCard";
import { Spinner } from "./Spinner";
import { ErrorText } from "./ErrorText";
import { secondaryButton } from "@/lib/ui";

export function PostList({
  fetchPage,
  resetKey,
  emptyMessage,
  header,
}: {
  fetchPage: (cursor: string | null) => Promise<Page<Post>>;
  resetKey: string;
  emptyMessage: string;
  header?: (actions: { prepend: (post: Post) => void }) => ReactNode;
}) {
  const { items, setItems, loading, error, hasMore, loadMore } = usePaginated<Post>(fetchPage, resetKey);

  return (
    <div className="space-y-4">
      {header?.({ prepend: (post) => setItems((previous) => [post, ...previous]) })}
      {items.map((post) => (
        <PostCard
          key={post.id}
          post={post}
          onUpdate={(next) => setItems((previous) => previous.map((p) => (p.id === next.id ? next : p)))}
          onDelete={(id) => setItems((previous) => previous.filter((p) => p.id !== id))}
        />
      ))}
      <ErrorText message={error} />
      {loading && <Spinner />}
      {!loading && !error && items.length === 0 && (
        <p className="rounded-2xl border border-dashed border-line p-8 text-center text-sm text-muted">
          {emptyMessage}
        </p>
      )}
      {!loading && hasMore && (
        <div className="flex justify-center">
          <button onClick={() => loadMore()} className={secondaryButton}>
            Load more
          </button>
        </div>
      )}
    </div>
  );
}
