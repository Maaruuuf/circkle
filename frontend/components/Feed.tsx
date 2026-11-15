"use client";

import { postsApi } from "@/lib/api";
import { PostComposer } from "./PostComposer";
import { PostList } from "./PostList";

export function Feed() {
  return (
    <>
      <h1 className="sr-only">Home feed</h1>
      <PostList
        fetchPage={postsApi.feed}
        resetKey="feed"
        emptyMessage="Your feed is empty. Follow people from Explore to see their posts here."
        header={({ prepend }) => <PostComposer onCreated={prepend} />}
      />
    </>
  );
}
