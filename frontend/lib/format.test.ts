import { describe, expect, it } from "vitest";
import { initials, pluralize, timeAgo } from "./format";

const now = new Date("2026-01-10T12:00:00Z");

describe("timeAgo", () => {
  it("handles recent times", () => {
    expect(timeAgo("2026-01-10T11:59:50Z", now)).toBe("just now");
    expect(timeAgo("2026-01-10T11:55:00Z", now)).toBe("5m");
    expect(timeAgo("2026-01-10T09:00:00Z", now)).toBe("3h");
    expect(timeAgo("2026-01-08T12:00:00Z", now)).toBe("2d");
  });

  it("never returns a negative time for clocks that are slightly ahead", () => {
    expect(timeAgo("2026-01-10T12:00:30Z", now)).toBe("just now");
  });
});

describe("initials", () => {
  it("uses first and last word", () => {
    expect(initials("Ada Lovelace")).toBe("AL");
    expect(initials("grace")).toBe("G");
    expect(initials("  ")).toBe("?");
  });
});

describe("pluralize", () => {
  it("adds an s except for one", () => {
    expect(pluralize(1, "post")).toBe("1 post");
    expect(pluralize(2, "post")).toBe("2 posts");
  });
});
