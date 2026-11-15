import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { fetchProfileServer } from "@/lib/server-api";
import { ProfileFallback, ProfileView } from "./ProfileView";

type Props = { params: { username: string } };

// Server-side rendered: the profile HTML (and its <title>/description) is ready for
// search engines and link previews. ProfileView then takes over in the browser.
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const result = await fetchProfileServer(params.username);
  if (result.status !== "ok") return { title: `@${params.username}` };
  const { profile } = result;
  return {
    title: `${profile.display_name} (@${profile.username})`,
    description: profile.bio ?? `${profile.display_name} on Circkle`,
  };
}

export default async function ProfilePage({ params }: Props) {
  const result = await fetchProfileServer(params.username);
  if (result.status === "missing") notFound();
  // Backend is waking up: let the browser load the profile instead of showing a false 404.
  if (result.status === "unavailable") return <ProfileFallback username={params.username} />;
  return <ProfileView initialProfile={result.profile} />;
}
