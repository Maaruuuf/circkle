"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/components/AuthContext";
import { Avatar } from "@/components/Avatar";
import { ErrorText } from "@/components/ErrorText";
import { PostCard } from "@/components/PostCard";
import { Spinner } from "@/components/Spinner";
import { ApiError, commentsApi, errorMessage, postsApi } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { Comment, Post } from "@/lib/types";
import { inputClass, primaryButton, secondaryButton } from "@/lib/ui";
import { usePaginated } from "@/lib/usePaginated";

export default function PostPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [post, setPost] = useState<Post | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const comments = usePaginated<Comment>((cursor) => commentsApi.list(id, cursor), `comments:${id}`);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    postsApi
      .get(id)
      .then(setPost)
      .catch((caught) => {
        if (caught instanceof ApiError && caught.status === 404) setNotFound(true);
        else setLoadError(errorMessage(caught));
      });
  }, [id, user?.id]);

  const addComment = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      if (!text.trim()) return;
      setBusy(true);
      setFormError(null);
      try {
        const created = await commentsApi.create(id, text.trim());
        comments.setItems((previous) => [...previous, created]);
        setPost((previous) => (previous ? { ...previous, comment_count: previous.comment_count + 1 } : previous));
        setText("");
      } catch (caught) {
        setFormError(errorMessage(caught));
      } finally {
        setBusy(false);
      }
    },
    [id, text, comments],
  );

  const removeComment = async (comment: Comment) => {
    try {
      await commentsApi.remove(comment.id);
      comments.setItems((previous) => previous.filter((c) => c.id !== comment.id));
      setPost((previous) => (previous ? { ...previous, comment_count: Math.max(0, previous.comment_count - 1) } : previous));
    } catch (caught) {
      setFormError(errorMessage(caught));
    }
  };

  if (notFound) return <p className="p-8 text-center text-muted">This post does not exist or was removed.</p>;
  if (loadError) return <ErrorText message={loadError} />;
  if (!post) return <Spinner />;

  return (
    <div className="space-y-4">
      <PostCard post={post} onUpdate={setPost} onDelete={() => (window.location.href = "/")} />

      <section aria-labelledby="comments-heading" className="rounded-2xl border border-line bg-surface p-3">
        <h2 id="comments-heading" className="mb-3 text-sm font-semibold">Comments</h2>
        <ul className="space-y-3">
          {comments.items.map((comment) => (
            <li key={comment.id} className="flex gap-2">
              <Avatar name={comment.author.display_name} src={comment.author.avatar_url} size="sm" />
              <div className="min-w-0 flex-1">
                <p className="text-sm">
                  <Link href={`/u/${comment.author.username}`} className="font-semibold hover:underline">
                    {comment.author.username}
                  </Link>{" "}
                  <span className="whitespace-pre-wrap break-words">{comment.content}</span>
                </p>
                <p className="text-xs text-muted">
                  {timeAgo(comment.created_at)}
                  {user && (user.id === comment.author.id || user.id === post.author.id || user.role === "admin") && (
                    <button onClick={() => removeComment(comment)} className="ml-3 hover:text-danger">Delete</button>
                  )}
                </p>
              </div>
            </li>
          ))}
        </ul>
        {comments.loading && <Spinner />}
        {!comments.loading && comments.items.length === 0 && <p className="text-sm text-muted">No comments yet.</p>}
        {!comments.loading && comments.hasMore && (
          <button onClick={() => comments.loadMore()} className={`${secondaryButton} mt-3`}>Load more comments</button>
        )}

        {user ? (
          <form onSubmit={addComment} className="mt-4 space-y-2">
            <input
              value={text}
              onChange={(event) => setText(event.target.value)}
              maxLength={1000}
              placeholder="Add a comment…"
              aria-label="Add a comment"
              className={inputClass}
            />
            <ErrorText message={formError} />
            <button type="submit" disabled={busy || !text.trim()} className={primaryButton}>Comment</button>
          </form>
        ) : (
          <p className="mt-4 text-sm text-muted">
            <Link href={`/login?next=/p/${id}`} className="font-semibold text-brand">Log in</Link> to comment.
          </p>
        )}
      </section>
    </div>
  );
}
