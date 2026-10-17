import type {Metadata} from "next";
import {headers} from "next/headers";
import {ThemeProvider} from "next-themes";
import type {ReactNode} from "react";
import {siteConfig} from "@/lib/site-config";
import {siteUrl} from "@/lib/site-url";
import "./globals.css";

const analyticsEnabled =
  process.env.NODE_ENV === "production" && siteUrl.hostname === siteConfig.analyticsDomain;

export const metadata: Metadata = {
  metadataBase: siteUrl,
  title: {default: siteConfig.name, template: `%s | ${siteConfig.name}`},
  description: siteConfig.description,
  applicationName: siteConfig.name,
  authors: [{name: siteConfig.maintainer.name, url: siteConfig.maintainer.url}],
  creator: siteConfig.maintainer.name,
  publisher: siteConfig.maintainer.name,
  alternates: {canonical: "/"},
  openGraph: {
    type: "website",
    locale: siteConfig.openGraphLocale,
    url: "/",
    siteName: siteConfig.name,
    title: siteConfig.name,
    description: siteConfig.description,
    images: [{url: "/opengraph-image", width: 1200, height: 630, alt: siteConfig.name}],
  },
  twitter: {
    card: "summary_large_image",
    title: siteConfig.name,
    description: siteConfig.description,
    images: ["/opengraph-image"],
  },
  robots: {index: true, follow: true},
};

export default async function RootLayout({children}: Readonly<{children: ReactNode}>) {
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  return (
    <html lang={siteConfig.language} suppressHydrationWarning>
      <head>
        {analyticsEnabled ? (
          <script
            defer
            nonce={nonce}
            src="https://cloud.umami.is/script.js"
            data-domains={siteConfig.analyticsDomain}
            data-website-id="e3733fba-21a0-4663-9e54-9e6adab3e0d5"
          />
        ) : null}
      </head>
      <body>
        <ThemeProvider
          attribute="data-theme"
          nonce={nonce}
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
          storageKey="opportunities-theme"
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
