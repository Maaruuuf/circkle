"use client";

import { PostList } from "@/components/PostList";
import { postsApi } from "@/lib/api";

export default function ExplorePage() {
  return (
    <>
      <h1 className="mb-4 text-xl font-bold">Explore</h1>
      <PostList fetchPage={postsApi.explore} resetKey="explore" emptyMessage="No posts yet. Be the first!" />
    </>
  );
}
