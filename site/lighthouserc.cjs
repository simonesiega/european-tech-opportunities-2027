module.exports = {
  ci: {
    collect: {
      startServerCommand: "bun run start",
      startServerReadyPattern: "Ready in",
      url: ["http://127.0.0.1:3000/", "http://127.0.0.1:3000/?page=2"],
      numberOfRuns: 2,
      settings: {
        chromeFlags: "--no-sandbox --disable-dev-shm-usage",
        // The production-only analytics script is not part of the directory and must not
        // make a local CI audit depend on an external service.
        blockedUrlPatterns: ["https://cloud.umami.is/*", "https://gateway.umami.is/*"],
      },
    },
    assert: {
      assertions: {
        "categories:performance": ["error", {minScore: 0.8}],
        "categories:accessibility": ["error", {minScore: 0.95}],
        "categories:best-practices": ["error", {minScore: 0.95}],
        "categories:seo": ["error", {minScore: 0.95}],
        "cumulative-layout-shift": ["error", {maxNumericValue: 0.1}],
        "total-blocking-time": ["error", {maxNumericValue: 400}],
      },
    },
    upload: {target: "filesystem", outputDir: ".lighthouseci"},
  },
};
