import Link from "next/link";
import { Icon } from "./Icon";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";
import { inkButton, primaryButton } from "@/lib/ui";

const SAMPLE_ACTIVITY = [
  { text: "Ada shared a new photo", time: "2:14 AM", done: true },
  { text: "Grace commented on your post", time: "3:40 AM", done: true },
  { text: "Linus started following you", time: "4:05 AM", done: true },
  { text: "Margaret reacted ❤️ to your post", time: "now", done: false },
];

const FEATURES: { label: string; className: string }[] = [
  { label: "Photos", className: "font-serif text-2xl italic" },
  { label: "COMMENTS", className: "text-sm font-medium tracking-[0.25em]" },
  { label: "Reactions", className: "text-xl font-bold" },
  { label: "follow", className: "text-2xl font-light" },
  { label: "EXPLORE", className: "text-base font-extrabold" },
  { label: "Dark mode", className: "font-serif text-2xl italic" },
];

/** Decorative city scene (inline SVG, no image files needed). */
function CityScene() {
  return (
    <svg viewBox="0 0 400 520" className="h-full w-full" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Illustration of a city street">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8c8a85" />
          <stop offset="1" stopColor="#c9c5bc" />
        </linearGradient>
        <pattern id="windows" width="14" height="16" patternUnits="userSpaceOnUse">
          <rect x="3" y="3" width="7" height="9" fill="#ece6da" opacity="0.6" />
        </pattern>
      </defs>
      <rect width="400" height="520" fill="url(#sky)" />
      {/* far buildings */}
      <g fill="#7a7872">
        <rect x="10" y="150" width="70" height="260" />
        <rect x="95" y="110" width="60" height="300" />
        <rect x="250" y="130" width="70" height="280" />
        <rect x="330" y="170" width="70" height="240" />
      </g>
      {/* near buildings */}
      <g fill="#4f4d49">
        <rect x="-10" y="60" width="130" height="380" />
        <rect x="290" y="30" width="130" height="410" />
      </g>
      <g fill="url(#windows)">
        <rect x="-10" y="60" width="130" height="380" />
        <rect x="290" y="30" width="130" height="410" />
        <rect x="95" y="110" width="60" height="300" opacity="0.6" />
        <rect x="250" y="130" width="70" height="280" opacity="0.6" />
      </g>
      {/* street */}
      <polygon points="120,440 290,440 420,520 -20,520" fill="#2e2d2b" />
      <g stroke="#e8e2d6" strokeWidth="3" strokeDasharray="14 12" opacity="0.8">
        <line x1="205" y1="445" x2="205" y2="520" />
      </g>
    </svg>
  );
}

export function Landing() {
  return (
    <div className="overflow-x-hidden">
      {/* announcement bar */}
      <div className="bg-ink px-4 py-2 text-center text-xs font-medium text-canvas">
        <span className="mr-2 rounded-full border border-canvas/40 px-2 py-0.5 text-[10px] uppercase tracking-wide">New</span>
        Circkle is open: create your account in a minute{" "}
        <Link href="/register" className="underline underline-offset-2">
          Join now
        </Link>
      </div>

      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <div className="flex items-center gap-8">
          <Logo />
          <nav aria-label="Primary" className="hidden gap-6 text-sm text-muted md:flex">
            <Link href="/explore" className="hover:text-ink">Explore</Link>
            <Link href="/search" className="hover:text-ink">Search people</Link>
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Link href="/login" className="hidden text-sm font-medium hover:text-brand sm:block">Log in</Link>
          <Link href="/register" className={`${inkButton} !px-4 !py-2`}>Get started</Link>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl items-center gap-14 px-5 pb-16 pt-6 lg:grid-cols-2 lg:pt-12">
        {/* left: message */}
        <section>
          <h1 className="text-5xl font-extrabold leading-[0.95] tracking-tight sm:text-6xl lg:text-7xl">
            Share the moments
            <br />
            that{" "}
            <span className="relative inline-block font-serif font-normal italic">
              matter.
              <svg viewBox="0 0 220 14" className="absolute -bottom-2 left-0 h-3 w-full text-brand" fill="none" preserveAspectRatio="none" aria-hidden="true">
                <path d="M2 9 C 40 2, 80 13, 120 7 S 190 4, 218 8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
              </svg>
            </span>
          </h1>
          <p className="mt-8 max-w-md text-lg leading-relaxed text-muted">
            Circkle is a calm little corner of the internet. Post photos and thoughts, follow the people you care
            about, and react or comment without the noise.
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-4">
            <Link href="/register" className={`${primaryButton} !px-6 !py-3.5 text-base`}>
              Join Circkle <Icon name="arrow" className="h-4 w-4" />
            </Link>
            <Link href="/explore" className="group inline-flex items-center gap-3 text-sm font-semibold">
              <span className="flex h-11 w-11 items-center justify-center rounded-full border border-ink/70 transition group-hover:bg-ink group-hover:text-canvas">
                <Icon name="play" className="h-4 w-4" />
              </span>
              Browse public posts
            </Link>
          </div>

          <div className="mt-10 flex items-center gap-4">
            <div className="flex" aria-hidden="true">
              {["A", "G", "L", "M"].map((letter, index) => (
                <span
                  key={letter}
                  className={`-ml-2 flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold ring-2 ring-canvas first:ml-0 ${
                    ["bg-ink text-canvas", "bg-brand text-white", "bg-surface2 text-ink", "bg-brand-soft text-brand"][index]
                  }`}
                >
                  {letter}
                </span>
              ))}
            </div>
            <p className="text-sm text-muted">
              <span className="font-semibold text-ink">Free to join.</span> Sign up with email or Google.
            </p>
          </div>
        </section>

        {/* right: visual */}
        <section className="relative mx-auto w-full max-w-md lg:max-w-none" aria-label="Preview of Circkle">
          <div className="absolute -bottom-3 -right-3 h-full w-[96%] rounded-[2rem] bg-brand" aria-hidden="true" />
          <div className="relative h-[30rem] overflow-hidden rounded-[2rem] border border-line bg-surface2 dark:brightness-75 sm:h-[34rem]">
            <CityScene />
            <span className="absolute left-4 top-4 rounded-full bg-surface/90 px-3 py-1 text-xs font-medium text-ink backdrop-blur">
              📍 Your circle
            </span>
          </div>

          {/* floating card: activity bars */}
          <div className="absolute -right-2 top-10 w-44 rounded-2xl border border-line bg-surface p-4 shadow-float sm:-right-6">
            <p className="text-xs text-muted">Activity this week · sample</p>
            <p className="mt-1 text-2xl font-bold">
              Growing<span className="ml-1 text-xs font-normal text-muted">steadily</span>
            </p>
            <div className="mt-3 flex h-10 items-end gap-1.5" aria-hidden="true">
              {[30, 45, 35, 60, 50, 100, 70].map((height, index) => (
                <span
                  key={index}
                  style={{ height: `${height}%` }}
                  className={`w-full rounded-sm ${index === 5 ? "bg-ink" : "bg-line"}`}
                />
              ))}
            </div>
          </div>

          {/* floating card: sample notifications */}
          <div className="absolute -left-2 bottom-6 w-72 max-w-[85%] rounded-2xl border border-line bg-surface p-4 shadow-float sm:-left-8">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="text-sm font-semibold">While you were away</span>
              <span className="text-muted">sample</span>
            </div>
            <ul className="divide-y divide-line">
              {SAMPLE_ACTIVITY.map((item) => (
                <li key={item.text} className="flex items-center gap-3 py-2 text-xs">
                  <span
                    className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${
                      item.done ? "bg-ink text-canvas" : "border border-brand text-brand"
                    }`}
                  >
                    {item.done ? <Icon name="check" className="h-3 w-3" strokeWidth={3} /> : <span className="h-1.5 w-1.5 rounded-full bg-brand" />}
                  </span>
                  <span className="flex-1">{item.text}</span>
                  <span className={item.done ? "text-muted" : "font-semibold text-brand"}>{item.time}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </main>

      {/* feature strip */}
      <section className="border-t border-line" aria-label="What you can do on Circkle">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-10 lg:flex-row lg:items-center lg:justify-between">
          <p className="max-w-[11rem] text-xs text-muted">Everything you need, nothing you don&apos;t.</p>
          <ul className="flex flex-1 flex-wrap items-center justify-between gap-x-8 gap-y-4 text-muted">
            {FEATURES.map((feature) => (
              <li key={feature.label} className={feature.className}>
                {feature.label}
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
