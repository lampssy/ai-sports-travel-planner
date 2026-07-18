import { useId, type ElementType, type HTMLAttributes, type ReactNode } from "react";

export function SectionHeader({
  title,
  eyebrow,
  description,
  action,
  headingLevel = 2,
  className,
  ...headerProps
}: HTMLAttributes<HTMLElement> & {
  title: ReactNode;
  eyebrow?: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  headingLevel?: 2 | 3 | 4;
}) {
  const generatedId = useId();
  const headingId = `section-${generatedId}`;
  const labelledBy = headerProps["aria-labelledby"] ?? headingId;
  const Heading = `h${headingLevel}` as ElementType;

  return (
    <header
      {...headerProps}
      className={`snowcast-section-header${className ? ` ${className}` : ""}`}
      aria-labelledby={labelledBy}
    >
      <div className="snowcast-section-header__copy">
        {eyebrow ? (
          <p className="snowcast-section-header__eyebrow">{eyebrow}</p>
        ) : null}
        <Heading id={headingId} className="snowcast-section-header__title">
          {title}
        </Heading>
        {description ? (
          <p className="snowcast-section-header__description">{description}</p>
        ) : null}
      </div>
      {action ? <div className="snowcast-section-header__action">{action}</div> : null}
    </header>
  );
}
