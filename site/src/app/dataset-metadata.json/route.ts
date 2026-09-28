import {getPublicExport} from "@/lib/public-export";

export const dynamic = "force-dynamic";

export function GET() {
  return getPublicExport("metadata");
}
