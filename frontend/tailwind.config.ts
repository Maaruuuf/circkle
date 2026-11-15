import type { Config } from "tailwindcss";

// Every color is a CSS variable (see app/globals.css), so light and dark mode
// swap by toggling the `dark` class on <html>. No `dark:` prefixes needed in components.
const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: token("canvas"),
        surface: token("surface"),
        surface2: token("surface2"),
        line: token("line"),
        ink: token("ink"),
        muted: token("muted"),
        brand: token("brand"),
        "brand-soft": token("brand-soft"),
        danger: token("danger"),
        "danger-soft": token("danger-soft"),
        success: token("success"),
        "success-soft": token("success-soft"),
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        serif: ["var(--font-serif)", "Georgia", "Times New Roman", "serif"],
      },
      boxShadow: {
        float: "0 10px 30px -10px rgb(0 0 0 / 0.25)",
      },
    },
  },
  plugins: [],
};
export default config;
