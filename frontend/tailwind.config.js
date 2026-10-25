import { createRequire } from 'module';

var require = createRequire(import.meta.url);
var module = { exports: {} };

/** @type {import('tailwindcss').Config}
 * Colors are OKLCH tokens defined in index.css so the semantic layer lives in one place.
 */
const t = (v) => `oklch(var(${v}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: t("--bg"),
        surface: t("--surface"),
        surface2: t("--surface-2"),
        line: t("--line"),
        lineStrong: t("--line-strong"),
        ink: t("--text"),
        ink2: t("--text-2"),
        ink3: t("--text-3"),
        accent: t("--accent"),
        accentStrong: t("--accent-strong"),
        onAccent: t("--on-accent"),
        blue: t("--blue"),
        amber: t("--amber"),
        danger: t("--danger"),
        success: t("--success"),
      },
      fontFamily: { sans: ["IBM Plex Sans", "ui-sans-serif", "system-ui", "sans-serif"] },
      fontSize: {
        xs: ["12px", "16px"], sm: ["13px", "18px"], base: ["14px", "20px"], md: ["16px", "22px"], lg: ["20px", "26px"], xl: ["24px", "30px"],
      },
      boxShadow: { pop: "0 10px 28px -10px oklch(0 0 0 / 0.22), 0 1px 2px oklch(0 0 0 / 0.06)" },
      zIndex: { dropdown: "20", sticky: "30", backdrop: "40", sheet: "50", toast: "60" },
    },
  },
  plugins: [],
};
