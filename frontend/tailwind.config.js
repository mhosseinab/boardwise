/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      // Visual identity tokens (docs/SPEC.md "Visual identity"): the one
      // bright, warm, consumer-retail look in the portfolio set.
      colors: {
        sand: "#F7F9FA",
        surface: "#FFFFFF",
        border: "#E5EBEE",
        primary: {
          DEFAULT: "#0E7C86",
          50: "#EAF5F6",
        },
        accent: "#14B8C4",
        coral: "#FF6B5A",
        compat: {
          green: "#0E9F6E",
          red: "#EF4444",
          amber: "#F59E0B",
        },
      },
      fontFamily: {
        heading: ["Poppins", "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        card: "16px",
      },
      boxShadow: {
        soft: "0 2px 8px -2px rgba(14, 30, 37, 0.08)",
        "soft-lg": "0 12px 32px -8px rgba(14, 30, 37, 0.16)",
      },
      transitionDuration: {
        200: "200ms",
      },
    },
  },
  plugins: [],
};
