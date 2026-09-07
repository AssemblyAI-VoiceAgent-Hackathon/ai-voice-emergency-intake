import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        satoshi: ["Satoshi", "sans-serif"],
        sans: ["Satoshi", "sans-serif"],
      },
      colors: {
        background: "#000000",
        foreground: "#FFFFFF",
        aira: {
          bg: "#000000",
          text: "#FFFFFF",
          blue: "#3954C0",
          navy: "#080E29",
          gray: "#575757",
          red: "#FF3714",
        },
      },
    },
  },
  plugins: [],
};
export default config;
