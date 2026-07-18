import type { HTMLAttributes, ReactNode } from "react";

export type BadgeVariant =
  | "neutral"
  | "info"
  | "supported"
  | "warning"
  | "brand";

export function Badge({
  variant = "neutral",
  children,
  className,
  ...badgeProps
}: HTMLAttributes<HTMLSpanElement> & {
  variant?: BadgeVariant;
  children: ReactNode;
}) {
  return (
    <span
      {...badgeProps}
      className={`snowcast-badge snowcast-badge--${variant}${className ? ` ${className}` : ""}`}
    >
      {children}
    </span>
  );
}
