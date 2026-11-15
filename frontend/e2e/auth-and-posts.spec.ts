import { expect, test } from "@playwright/test";

// Requires the full stack (see docs/TESTING.md) and REQUIRE_EMAIL_VERIFICATION=false.
const unique = () => `e2e${Date.now().toString(36)}${Math.floor(Math.random() * 1000)}`;

test("guest sees the landing page at /", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Share the moments");
  await expect(page.getByRole("link", { name: /Join Circkle/ })).toBeVisible();
});

test("guest is sent to login when opening a protected page", async ({ page }) => {
  await page.goto("/settings");
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();
});

test("dark mode toggle switches the theme and is remembered", async ({ page }) => {
  await page.goto("/");
  const html = page.locator("html");
  await page.getByRole("button", { name: "Toggle dark mode" }).first().click();
  await expect(html).toHaveClass(/dark/);
  await page.reload();
  await expect(html).toHaveClass(/dark/);
});

test("register, log in, post, react, comment, log out", async ({ page }) => {
  const name = unique();
  const password = "e2e-password-123";

  await page.goto("/register");
  await page.getByLabel("Email").fill(`${name}@example.com`);
  await page.getByLabel("Username").fill(name);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign up" }).click();

  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel("Email").fill(`${name}@example.com`);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();

  await expect(page.getByLabel("Post text")).toBeVisible();
  await page.getByLabel("Post text").fill(`Hello from ${name}`);
  await page.getByRole("button", { name: "Post", exact: true }).click();
  await expect(page.getByText(`Hello from ${name}`)).toBeVisible();

  await page.getByRole("button", { name: "Love" }).first().click();
  await expect(page.getByRole("button", { name: "Love" }).first()).toHaveAttribute("aria-pressed", "true");

  await page.getByRole("link", { name: /comment/ }).first().click();
  await page.getByLabel("Add a comment").fill("first!");
  await page.getByRole("button", { name: "Comment", exact: true }).click();
  await expect(page.getByText("first!")).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login/);
});

test("wrong password shows a generic error", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("nobody@example.com");
  await page.getByLabel("Password").fill("not-a-real-password");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByRole("alert")).toContainText("Invalid email or password");
});

test("unknown profile shows the 404 page", async ({ page }) => {
  await page.goto("/u/this_user_does_not_exist");
  await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
});
