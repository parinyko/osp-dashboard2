import React from "react";

export default function ChartCard({ title, children, style, headerStyle }) {
  return (
    <div
      style={{
        background: "#fff",
        color: "#1f1f2c",
        borderRadius: 12,
        boxShadow: "0 8px 28px rgba(0,0,0,0.18)",
        overflow: "hidden",
        ...style,
      }}
    >
      {title ? (
        <div
          style={{
            background: "linear-gradient(180deg, #BCE49A, #A8D75A)",
            color: "#1d3d11",
            fontWeight: 700,
            fontSize: 15,
            padding: "10px 16px",
            textAlign: "center",
            ...headerStyle,
          }}
        >
          {title}
        </div>
      ) : null}
      <div style={{ padding: 12 }}>{children}</div>
    </div>
  );
}
