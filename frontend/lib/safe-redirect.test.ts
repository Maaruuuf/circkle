import { describe, expect, it } from "vitest";
import { safeNextPath } from "./safe-redirect";

describe("safeNextPath", () => {
  it("allows in-app paths", () => {
    expect(safeNextPath("/settings")).toBe("/settings");
    expect(safeNextPath("/u/ada?tab=posts")).toBe("/u/ada?tab=posts");
  });

  it("blocks external and protocol-relative URLs", () => {
    expect(safeNextPath("https://evil.com")).toBe("/");
    expect(safeNextPath("//evil.com")).toBe("/");
    expect(safeNextPath("/\\evil.com")).toBe("/");
    expect(safeNextPath("javascript:alert(1)")).toBe("/");
  });

  it("falls back when missing", () => {
    expect(safeNextPath(null)).toBe("/");
    expect(safeNextPath(undefined, "/home")).toBe("/home");
  });
});
