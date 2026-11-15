const MINUTE = 60;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** "just now", "5m", "3h", "2d", or a short date for older items. */
export function timeAgo(isoDate: string, now: Date = new Date()): string {
  const seconds = Math.max(0, Math.floor((now.getTime() - new Date(isoDate).getTime()) / 1000));
  if (seconds < 45) return "just now";
  if (seconds < HOUR) return `${Math.max(1, Math.floor(seconds / MINUTE))}m`;
  if (seconds < DAY) return `${Math.floor(seconds / HOUR)}h`;
  if (seconds < 7 * DAY) return `${Math.floor(seconds / DAY)}d`;
  return new Date(isoDate).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0][0] ?? "?";
  const second = parts.length > 1 ? parts[parts.length - 1][0] ?? "" : "";
  return (first + second).toUpperCase();
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}
