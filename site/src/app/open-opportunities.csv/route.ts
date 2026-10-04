import {getPublicExport} from "@/lib/public-export";

export const dynamic = "force-dynamic";

export function GET() {
  return getPublicExport("csv");
}

export function HEAD() {
  return getPublicExport("csv", true);
}
