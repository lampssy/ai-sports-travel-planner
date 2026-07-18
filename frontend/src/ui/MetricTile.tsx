import type { HTMLAttributes, ReactNode } from "react";

export function MetricTile({
  label,
  value,
  detail,
  icon,
  className,
  ...tileProps
}: HTMLAttributes<HTMLDivElement> & {
  label: ReactNode;
  value: ReactNode;
  detail?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div
      {...tileProps}
      className={`snowcast-metric-tile${className ? ` ${className}` : ""}`}
    >
      {icon ? <span className="snowcast-metric-tile__icon">{icon}</span> : null}
      <p className="snowcast-metric-tile__label">{label}</p>
      <p className="snowcast-metric-tile__value">{value}</p>
      {detail ? <p className="snowcast-metric-tile__detail">{detail}</p> : null}
    </div>
  );
}
