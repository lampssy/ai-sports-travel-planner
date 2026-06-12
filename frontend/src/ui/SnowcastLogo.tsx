export function SnowcastLogo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={`relative flex shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-white text-midnight shadow-sm ${
          compact ? "h-10 w-10" : "h-12 w-12"
        }`}
        aria-hidden="true"
      >
        <svg
          viewBox="0 0 48 48"
          className={compact ? "h-8 w-8" : "h-9 w-9"}
          role="img"
        >
          <path
            d="M4 37 17.5 13.5 26 28l5-8.7L44 37H4Z"
            fill="currentColor"
          />
          <path
            d="m17.5 13.5 4.8 8.2-5.5 2.5-2.7-4.7 3.4-6Z"
            fill="#f8fbff"
          />
          <path
            d="M35.5 7v10M30.5 12h10M32 8.5l7 7M39 8.5l-7 7"
            stroke="#0b5fb8"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      </div>
      <div className={compact ? "hidden sm:block" : ""}>
        <p className="font-display text-xl font-semibold leading-none tracking-tight text-white">
          SNOWCAST
        </p>
        {!compact ? (
          <p className="mt-1 text-xs font-semibold uppercase tracking-[0.16em] text-white/58">
            Snow-aware planning
          </p>
        ) : null}
      </div>
    </div>
  );
}
