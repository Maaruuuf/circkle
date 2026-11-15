"use client";

import Link from "next/link";
import { useState } from "react";
import { errorMessage, postsApi } from "@/lib/api";
import { pluralize, timeAgo } from "@/lib/format";
import type { Post } from "@/lib/types";
import { useAuth } from "./AuthContext";
import { Avatar } from "./Avatar";
import { ReactionBar } from "./ReactionBar";

export function PostCard({
  post,
  onUpdate,
  onDelete,
}: {
  post: Post;
  onUpdate: (post: Post) => void;
  onDelete: (id: string) => void;
}) {
  const { user } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const canDelete = user && (user.id === post.author.id || user.role === "admin");

  const handleDelete = async () => {
    if (!window.confirm("Delete this post? This cannot be undone.")) return;
    try {
      await postsApi.remove(post.id);
      onDelete(post.id);
    } catch (caught) {
      setError(errorMessage(caught));
    }
  };

  return (
    <article className="overflow-hidden rounded-2xl border border-line bg-surface">
      <header className="flex items-center gap-3 p-3">
        <Avatar name={post.author.display_name} src={post.author.avatar_url} />
        <div className="min-w-0 flex-1">
          <Link href={`/u/${post.author.username}`} className="block truncate text-sm font-semibold hover:underline">
            {post.author.display_name}
          </Link>
          <p className="text-xs text-muted">
            @{post.author.username} · {timeAgo(post.created_at)}
          </p>
        </div>
        {canDelete && (
          <button
            onClick={handleDelete}
            className="rounded px-2 py-1 text-xs font-medium text-muted hover:bg-danger-soft hover:text-danger"
          >
            Delete
          </button>
        )}
      </header>

      {post.image_url && (
        <img src={post.image_url} alt={`Photo by ${post.author.username}`} className="max-h-[32rem] w-full object-cover" />
      )}
      {post.content && <p className="whitespace-pre-wrap break-words px-3 py-3 text-sm">{post.content}</p>}

      <footer className="flex items-center justify-between border-t border-line px-3 py-2">
        <ReactionBar
          post={post}
          onChange={(next) => onUpdate({ ...post, reaction_count: next.reaction_count, my_reaction: next.my_reaction })}
        />
        <Link href={`/p/${post.id}`} className="text-sm text-muted hover:text-brand">
          {pluralize(post.comment_count, "comment")}
        </Link>
      </footer>
      {error && <p role="alert" className="px-3 pb-2 text-xs text-danger">{error}</p>}
    </article>
  );
}
