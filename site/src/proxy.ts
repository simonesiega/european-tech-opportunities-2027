import {randomBytes} from "node:crypto";
import {NextResponse, type NextRequest} from "next/server";
import {contentSecurityPolicy} from "@/lib/content-security-policy";

export function proxy(request: NextRequest) {
  if (process.env.NODE_ENV !== "production") return NextResponse.next();

  const nonce = randomBytes(32).toString("base64");
  const policy = contentSecurityPolicy(nonce);
  const headers = new Headers(request.headers);
  // Never trust nonce or CSP values supplied by the caller.
  headers.set("x-nonce", nonce);
  headers.set("Content-Security-Policy", policy);
  const response = NextResponse.next({request: {headers}});
  response.headers.set("Content-Security-Policy", policy);
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image).*)"],
};
