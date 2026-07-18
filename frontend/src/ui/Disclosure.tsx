import type { DetailsHTMLAttributes, ReactNode } from "react";

export function Disclosure({
  label,
  children,
  className,
  ...detailsProps
}: DetailsHTMLAttributes<HTMLDetailsElement> & {
  label: ReactNode;
  children: ReactNode;
}) {
  return (
    <details
      {...detailsProps}
      className={`snowcast-disclosure${className ? ` ${className}` : ""}`}
    >
      <summary className="snowcast-disclosure__summary" tabIndex={0}>
        {label}
      </summary>
      <div className="snowcast-disclosure__content">{children}</div>
    </details>
  );
}
