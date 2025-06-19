import * as React from "react";

interface AuroraTextProps extends React.HTMLAttributes<HTMLSpanElement> {
  children: React.ReactNode;
  colors?: string[];
  speed?: number;
}

export function AuroraText({
  children,
  className = "",
  colors = ["#FF0080", "#7928CA", "#0070F3", "#38bdf8"],
  speed = 1,
  ...props
}: AuroraTextProps) {
  const style: React.CSSProperties = {
    backgroundImage: `linear-gradient(90deg, ${colors.join(",")})`,
    backgroundSize: "400%",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
    animation: `auroraShift ${6 / speed}s linear infinite`,
  };

  return (
    <span className={className} style={style} {...props}>
      {children}
    </span>
  );
}
