import {ImageResponse} from "next/og";

export const alt = "European Tech Opportunities 2027 directory";
export const size = {width: 1200, height: 630};
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    <div
      style={{
        alignItems: "center",
        background: "linear-gradient(135deg, #01123c 0%, #123071 55%, #315db8 100%)",
        color: "white",
        display: "flex",
        height: "100%",
        justifyContent: "center",
        padding: "72px",
        width: "100%",
      }}
    >
      <div
        style={{
          border: "2px solid rgba(255,255,255,0.24)",
          borderRadius: "36px",
          display: "flex",
          flexDirection: "column",
          gap: "30px",
          padding: "70px",
          width: "100%",
        }}
      >
        <div style={{color: "#a9c5ff", display: "flex", fontSize: 30, letterSpacing: 3}}>
          OPPORTUNITIES ’27
        </div>
        <div style={{display: "flex", fontSize: 72, fontWeight: 700, lineHeight: 1.05}}>
          European Tech Opportunities 2027
        </div>
        <div style={{color: "#dce8ff", display: "flex", fontSize: 32}}>
          Discover open technology opportunities across Europe.
        </div>
      </div>
    </div>,
    size
  );
}
