import type {MetadataRoute} from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    scope: "/",
    start_url: "/",
    name: "European Tech Internships 2027",
    short_name: "Internships ’27",
    description: "Open European technology internships and New Grad roles for 2027.",
    lang: "en-GB",
    dir: "ltr",
    display: "standalone",
    background_color: "#f9fafb",
    theme_color: "#01123c",
    icons: [{src: "/icon.svg", sizes: "any", type: "image/svg+xml"}],
  };
}
