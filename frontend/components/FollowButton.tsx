"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { usersApi } from "@/lib/api";
import { primaryButton, secondaryButton } from "@/lib/ui";
import { useAuth } from "./AuthContext";

export function FollowButton({
  username,
  isFollowing,
  onChange,
}: {
  username: string;
  isFollowing: boolean;
  onChange: (following: boolean) => void;
}) {
  const { user } = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  const toggle = async () => {
    if (!user) return router.push(`/login?next=${encodeURIComponent(`/u/${username}`)}`);
    setBusy(true);
    try {
      if (isFollowing) await usersApi.unfollow(username);
      else await usersApi.follow(username);
      onChange(!isFollowing);
    } finally {
      setBusy(false);
    }
  };

  return (
    <button onClick={toggle} disabled={busy} className={isFollowing ? secondaryButton : primaryButton}>
      {isFollowing ? "Following" : "Follow"}
    </button>
  );
}
