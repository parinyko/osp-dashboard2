import React from "react";

export default function PageHeader({ title, subtitle }) {
  return (
    <div
      style={{
        background:
          "linear-gradient(90deg, #A8D75A 0%, #C9CB4D 35%, #F5B642 100%)",
        padding: "18px 32px",
        borderRadius: 8,
        marginBottom: 20,
        boxShadow: "0 6px 24px rgba(0,0,0,0.25)",
      }}
    >
      <div
        style={{
          color: "#fff",
          fontSize: 24,
          fontWeight: 600,
          letterSpacing: "-0.01em",
          textShadow: "0 1px 2px rgba(0,0,0,0.25)",
        }}
      >
        Monthly Report : {title}
      </div>
      {subtitle ? (
        <div
          style={{
            marginTop: 4,
            color: "rgba(255,255,255,0.85)",
            fontSize: 13,
          }}
        >
          {subtitle}
        </div>
      ) : null}
    </div>
  );
}
