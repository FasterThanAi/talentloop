/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        border: "var(--border)",
        text: "var(--text)",
        "text-muted": "var(--text-muted)",
        primary: "var(--primary)",
        "primary-weak": "var(--primary-weak)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        evidence: "var(--evidence)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
      },
      boxShadow: {
        sm: "0 1px 2px rgb(15 23 42 / 0.06)",
        card: "0 1px 2px rgb(15 23 42 / 0.06)",
      },
      borderRadius: {
        control: "6px",
        card: "10px",
        pill: "999px",
      }
    },
  },
  plugins: [],
};
