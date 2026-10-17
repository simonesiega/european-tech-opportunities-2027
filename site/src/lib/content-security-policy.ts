export function contentSecurityPolicy(nonce?: string): string {
  return [
    "default-src 'self'",
    "base-uri 'self'",
    "connect-src 'self' https://gateway.umami.is",
    "font-src 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "img-src 'self' data: blob:",
    "object-src 'none'",
    `script-src 'self'${nonce ? ` 'nonce-${nonce}' 'strict-dynamic'` : ""} https://cloud.umami.is`,
    "script-src-attr 'none'",
    // The floating action menu and theme provider use inline styles, not scripts.
    "style-src 'self' 'unsafe-inline'",
  ].join("; ");
}
