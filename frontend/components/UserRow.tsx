import Link from "next/link";
import type { UserSummary } from "@/lib/types";
import { Avatar } from "./Avatar";

export function UserRow({ user }: { user: UserSummary }) {
  return (
    <li>
      <Link href={`/u/${user.username}`} className="flex items-center gap-3 rounded-xl p-2 hover:bg-surface2">
        <Avatar name={user.display_name} src={user.avatar_url} />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{user.display_name}</p>
          <p className="truncate text-xs text-muted">@{user.username}</p>
        </div>
      </Link>
    </li>
  );
}
