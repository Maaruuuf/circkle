"use client";

import { PostComposer } from "@/components/PostComposer";
import { PostList } from "@/components/PostList";
import { RequireAuth } from "@/components/RequireAuth";
import { postsApi } from "@/lib/api";

export default function HomePage() {
  return (
    <RequireAuth>
      <h1 className="sr-only">Home feed</h1>
      <PostList
        fetchPage={postsApi.feed}
        resetKey="feed"
        emptyMessage="Your feed is empty. Follow people from Explore to see their posts here."
        header={({ prepend }) => <PostComposer onCreated={prepend} />}
      />
    </RequireAuth>
  );
}
