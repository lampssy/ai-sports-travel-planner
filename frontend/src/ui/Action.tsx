import { forwardRef, type ButtonHTMLAttributes } from "react";

export type ActionVariant = "primary" | "secondary" | "ghost" | "danger";
export type ActionSize = "sm" | "md";

type SharedActionProps = Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  "aria-label"
> & {
  variant?: ActionVariant;
  size?: ActionSize;
};

export type ActionProps = SharedActionProps &
  (
    | {
        iconOnly: true;
        "aria-label": string;
      }
    | {
        iconOnly?: false;
        "aria-label"?: string;
      }
  );

export const Action = forwardRef<HTMLButtonElement, ActionProps>(function Action(
  {
    variant = "primary",
    size = "md",
    iconOnly = false,
    className,
    type = "button",
    ...buttonProps
  },
  ref,
) {
  if (iconOnly && !buttonProps["aria-label"]?.trim()) {
    throw new Error("Icon-only actions require an aria-label.");
  }

  const classes = [
    "snowcast-action",
    `snowcast-action--${variant}`,
    `snowcast-action--${size}`,
    iconOnly ? "snowcast-action--icon-only" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return <button ref={ref} {...buttonProps} type={type} className={classes} />;
});
