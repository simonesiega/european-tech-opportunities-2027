import type {Metadata} from "next";
import {ThemeProvider} from "next-themes";
import type {ReactNode} from "react";
import "./globals.css";

const siteUrl = process.env.SITE_URL ?? "http://localhost:3000";
const title = "European Tech Opportunities 2027";
const description =
  "Search and filter 2027 technology internships and New Grad positions across Europe.";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {default: title, template: `%s | ${title}`},
  description,
  applicationName: title,
  authors: [{name: "Simone Siega", url: "https://simonesiega.com"}],
  creator: "Simone Siega",
  publisher: "Simone Siega",
  alternates: {canonical: "/"},
  openGraph: {
    type: "website",
    locale: "en_GB",
    url: "/",
    siteName: title,
    title,
    description,
    images: [{url: "/opengraph-image", width: 1200, height: 630, alt: title}],
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
    images: ["/opengraph-image"],
  },
  robots: {index: true, follow: true},
};

export default function RootLayout({children}: Readonly<{children: ReactNode}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          defer
          src="https://cloud.umami.is/script.js"
          data-website-id="e3733fba-21a0-4663-9e54-9e6adab3e0d5"
        />
      </head>
      <body>
        <ThemeProvider
          attribute="data-theme"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
          storageKey="internships-theme"
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
