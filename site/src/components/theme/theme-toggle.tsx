"use client";

import {useTheme} from "next-themes";

function ThemeIcon() {
  return (
    <span className="theme-icon" aria-hidden="true">
      <svg className="sun-icon" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="3.5" />
        <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42" />
      </svg>
      <svg className="moon-icon" viewBox="0 0 24 24">
        <path d="M20.2 15.1A8.5 8.5 0 0 1 8.9 3.8a8.5 8.5 0 1 0 11.3 11.3Z" />
      </svg>
    </span>
  );
}

export function ThemeToggle() {
  const {resolvedTheme, setTheme} = useTheme();

  function toggleTheme() {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  }

  return (
    <button
      className="theme-toggle"
      type="button"
      onClick={toggleTheme}
      aria-label="Toggle color theme"
    >
      <ThemeIcon />
    </button>
  );
}
