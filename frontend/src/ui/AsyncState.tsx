import type { ReactNode } from "react";

import { Action } from "./Action";

export type AsyncStateKind = "loading" | "empty" | "error";

export function AsyncState({
  state,
  message,
  title,
  onRetry,
  retryLabel = "Try again",
  retrying = false,
  className,
}: {
  state: AsyncStateKind;
  message: ReactNode;
  title?: ReactNode;
  onRetry?: () => void;
  retryLabel?: string;
  retrying?: boolean;
  className?: string;
}) {
  const isError = state === "error";

  return (
    <div
      className={`snowcast-async-state snowcast-async-state--${state}${className ? ` ${className}` : ""}`}
      role={isError ? "alert" : "status"}
      aria-live={isError ? "assertive" : "polite"}
      aria-busy={state === "loading" || retrying ? "true" : undefined}
    >
      {state === "loading" ? (
        <span className="snowcast-async-state__indicator" aria-hidden="true" />
      ) : null}
      <div className="snowcast-async-state__copy">
        {title ? <h2 className="snowcast-async-state__title">{title}</h2> : null}
        <div className="snowcast-async-state__message">{message}</div>
      </div>
      {isError && onRetry ? (
        <Action
          variant="secondary"
          size="sm"
          disabled={retrying}
          onClick={onRetry}
        >
          {retryLabel}
        </Action>
      ) : null}
    </div>
  );
}
