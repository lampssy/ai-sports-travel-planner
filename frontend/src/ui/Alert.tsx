import type { HTMLAttributes, ReactNode } from "react";

export type AlertVariant = "info" | "success" | "warning" | "error";

export function Alert({
  variant,
  live = "off",
  children,
  className,
  ...alertProps
}: Omit<HTMLAttributes<HTMLDivElement>, "role" | "aria-live"> & {
  variant: AlertVariant;
  live?: "off" | "polite" | "assertive";
  children: ReactNode;
}) {
  const liveRegionProps =
    live === "assertive"
      ? { role: "alert", "aria-live": "assertive" as const }
      : live === "polite"
        ? { role: "status", "aria-live": "polite" as const }
        : {};

  return (
    <div
      {...alertProps}
      {...liveRegionProps}
      className={`snowcast-alert snowcast-alert--${variant}${className ? ` ${className}` : ""}`}
    >
      {children}
    </div>
  );
}
