"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { errorMessage, mediaApi, postsApi } from "@/lib/api";
import type { Post } from "@/lib/types";
import { inputClass, primaryButton, secondaryButton } from "@/lib/ui";
import { useAuth } from "./AuthContext";
import { Avatar } from "./Avatar";
import { ErrorText } from "./ErrorText";

const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

export function PostComposer({ onCreated }: { onCreated: (post: Post) => void }) {
  const { user } = useAuth();
  const [content, setContent] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  if (!user) return null;

  const chooseFile = (candidate: File | undefined) => {
    setError(null);
    if (!candidate) return;
    // Client-side checks are only a convenience: the server validates again.
    if (!ALLOWED_TYPES.includes(candidate.type)) return setError("Please choose a JPEG, PNG or WebP image.");
    if (candidate.size > MAX_BYTES) return setError("Image must be smaller than 5 MB.");
    setFile(candidate);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!content.trim() && !file) return setError("Write something or add a photo.");
    setBusy(true);
    setError(null);
    try {
      const media = file ? await mediaApi.uploadImage(file) : null;
      const post = await postsApi.create({ content: content.trim() || null, media_id: media?.id ?? null });
      onCreated(post);
      setContent("");
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-3 rounded-2xl border border-line bg-surface p-3">
      <div className="flex gap-3">
        <Avatar name={user.display_name} src={user.avatar_url} />
        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          maxLength={2000}
          rows={3}
          placeholder="What's happening?"
          aria-label="Post text"
          className={inputClass}
        />
      </div>
      {preview && (
        <div className="relative">
          <img src={preview} alt="Selected upload preview" className="max-h-64 w-full rounded-xl object-cover" />
          <button
            type="button"
            onClick={() => setFile(null)}
            className="absolute right-2 top-2 rounded-full bg-ink/70 px-3 py-1 text-xs text-canvas"
          >
            Remove
          </button>
        </div>
      )}
      <ErrorText message={error} />
      <div className="flex items-center justify-between">
        <label className={`${secondaryButton} cursor-pointer`}>
          📷 Photo
          <input
            ref={fileInput}
            type="file"
            accept={ALLOWED_TYPES.join(",")}
            className="sr-only"
            onChange={(event) => chooseFile(event.target.files?.[0])}
          />
        </label>
        <button type="submit" disabled={busy} className={primaryButton}>
          {busy ? "Posting…" : "Post"}
        </button>
      </div>
    </form>
  );
}
