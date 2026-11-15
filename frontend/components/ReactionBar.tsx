"use client";

import { useState } from "react";
import { postsApi } from "@/lib/api";
import type { Post, ReactionType } from "@/lib/types";
import { useAuth } from "./AuthContext";

const REACTIONS: { type: ReactionType; emoji: string; label: string }[] = [
  { type: "like", emoji: "👍", label: "Like" },
  { type: "love", emoji: "❤️", label: "Love" },
  { type: "haha", emoji: "😂", label: "Haha" },
  { type: "wow", emoji: "😮", label: "Wow" },
  { type: "sad", emoji: "😢", label: "Sad" },
];

export function ReactionBar({
  post,
  onChange,
}: {
  post: Pick<Post, "id" | "reaction_count" | "my_reaction">;
  onChange: (next: { reaction_count: number; my_reaction: ReactionType | null }) => void;
}) {
  const { user } = useAuth();
  const [busy, setBusy] = useState(false);

  const toggle = async (type: ReactionType) => {
    if (!user || busy) return;
    const removing = post.my_reaction === type;
    const before = { reaction_count: post.reaction_count, my_reaction: post.my_reaction };
    // Optimistic update: show the change immediately, roll back if the server refuses.
    const delta = removing ? -1 : post.my_reaction ? 0 : 1;
    onChange({ reaction_count: post.reaction_count + delta, my_reaction: removing ? null : type });
    setBusy(true);
    try {
      const summary = removing ? await postsApi.unreact(post.id) : await postsApi.react(post.id, type);
      onChange({ reaction_count: summary.reaction_count, my_reaction: summary.my_reaction });
    } catch {
      onChange(before);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex items-center gap-1" role="group" aria-label="Reactions">
      {REACTIONS.map(({ type, emoji, label }) => (
        <button
          key={type}
          type="button"
          onClick={() => toggle(type)}
          disabled={!user}
          aria-label={label}
          aria-pressed={post.my_reaction === type}
          title={user ? label : "Log in to react"}
          className={`rounded-full px-2 py-1 text-lg transition hover:bg-surface2 disabled:opacity-60 ${
            post.my_reaction === type ? "bg-brand-soft ring-1 ring-brand" : ""
          }`}
        >
          {emoji}
        </button>
      ))}
      <span className="ml-2 text-sm text-muted" aria-live="polite">
        {post.reaction_count}
      </span>
    </div>
  );
}
