import {getOpenInternships} from "@/lib/internships";

export const dynamic = "force-dynamic";

export default function Home() {
  const openInternships = getOpenInternships();

  return (
    <main>
      <h1>European Tech Internships 2027</h1>
      <p>{openInternships.length} open internships</p>
    </main>
  );
}
