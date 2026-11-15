"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthContext";
import { Avatar } from "@/components/Avatar";
import { FollowButton } from "@/components/FollowButton";
import { PostList } from "@/components/PostList";
import { UserRow } from "@/components/UserRow";
import { Spinner } from "@/components/Spinner";
import { postsApi, usersApi } from "@/lib/api";
import { secondaryButton } from "@/lib/ui";
import type { Page, PublicProfile, UserSummary } from "@/lib/types";
import { usePaginated } from "@/lib/usePaginated";

type Tab = "posts" | "followers" | "following";

function PeopleList({ fetchPage, resetKey }: { fetchPage: (c: string | null) => Promise<Page<UserSummary>>; resetKey: string }) {
  const { items, loading, hasMore, loadMore } = usePaginated<UserSummary>(fetchPage, resetKey);
  return (
    <div className="rounded-2xl border border-line bg-surface p-2">
      <ul>{items.map((user) => <UserRow key={user.id} user={user} />)}</ul>
      {loading && <Spinner />}
      {!loading && items.length === 0 && <p className="p-4 text-center text-sm text-muted">Nobody here yet.</p>}
      {!loading && hasMore && (
        <div className="flex justify-center p-2">
          <button onClick={() => loadMore()} className={secondaryButton}>Load more</button>
        </div>
      )}
    </div>
  );
}

export function ProfileView({ initialProfile }: { initialProfile: PublicProfile }) {
  const { user, status } = useAuth();
  const [profile, setProfile] = useState(initialProfile);
  const [tab, setTab] = useState<Tab>("posts");
  const username = initialProfile.username;

  // The server render has no cookies, so fetch again in the browser to learn
  // viewer-specific data (is_me, is_following) once we know who is logged in.
  useEffect(() => {
    if (status === "loading") return;
    usersApi.profile(username).then(setProfile).catch(() => undefined);
  }, [username, status, user?.id]);

  const onFollowChange = (following: boolean) =>
    setProfile((previous) => ({
      ...previous,
      is_following: following,
      followers_count: previous.followers_count + (following ? 1 : -1),
    }));

  const stat = (label: string, value: number, target?: Tab) => (
    <button
      type="button"
      onClick={() => target && setTab(target)}
      disabled={!target}
      className="text-center disabled:cursor-default"
    >
      <span className="block text-lg font-bold">{value}</span>
      <span className="text-xs text-muted">{label}</span>
    </button>
  );

  return (
    <>
      <header className="mb-4 rounded-2xl border border-line bg-surface p-4">
        <div className="flex items-center gap-4">
          <Avatar name={profile.display_name} src={profile.avatar_url} size="lg" />
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-xl font-bold">{profile.display_name}</h1>
            <p className="text-sm text-muted">@{profile.username}</p>
          </div>
          {profile.is_me ? (
            <Link href="/settings" className={secondaryButton}>Edit profile</Link>
          ) : (
            <FollowButton username={profile.username} isFollowing={profile.is_following} onChange={onFollowChange} />
          )}
        </div>
        {profile.bio && <p className="mt-3 whitespace-pre-wrap text-sm">{profile.bio}</p>}
        <div className="mt-4 flex justify-around border-t border-line pt-3">
          {stat("posts", profile.posts_count, "posts")}
          {stat("followers", profile.followers_count, "followers")}
          {stat("following", profile.following_count, "following")}
        </div>
      </header>

      {tab === "posts" && (
        <PostList
          fetchPage={(cursor) => postsApi.byUser(username, cursor)}
          resetKey={`posts:${username}:${user?.id ?? "guest"}`}
          emptyMessage="No posts yet."
        />
      )}
      {tab === "followers" && (
        <PeopleList fetchPage={(cursor) => usersApi.followers(username, cursor)} resetKey={`followers:${username}`} />
      )}
      {tab === "following" && (
        <PeopleList fetchPage={(cursor) => usersApi.following(username, cursor)} resetKey={`following:${username}`} />
      )}
    </>
  );
}

/** Used when the server could not reach the backend: load the profile in the browser. */
export function ProfileFallback({ username }: { username: string }) {
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    usersApi.profile(username).then(setProfile).catch(() => setFailed(true));
  }, [username]);

  if (failed) return <p className="p-8 text-center text-muted">This profile could not be loaded.</p>;
  if (!profile) return <Spinner />;
  return <ProfileView initialProfile={profile} />;
}
