import { initials } from "@/lib/format";

const SIZES = { sm: "h-8 w-8 text-xs", md: "h-10 w-10 text-sm", lg: "h-24 w-24 text-2xl" } as const;

export function Avatar({
  name,
  src,
  size = "md",
}: {
  name: string;
  src: string | null | undefined;
  size?: keyof typeof SIZES;
}) {
  const classes = `${SIZES[size]} shrink-0 rounded-full object-cover`;
  if (src) return <img src={src} alt="" className={classes} />;
  return (
    <span
      aria-hidden="true"
      className={`${classes} flex items-center justify-center bg-brand-soft font-semibold text-brand`}
    >
      {initials(name)}
    </span>
  );
}
