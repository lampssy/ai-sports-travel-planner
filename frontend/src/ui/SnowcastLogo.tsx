export function SnowcastLogo({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`snowcast-logo${compact ? " snowcast-logo--compact" : ""}`}>
      <div
        className="snowcast-logo__mark"
        aria-hidden="true"
      >
        <svg viewBox="0 0 48 48" role="img">
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
      <div>
        <p className="snowcast-logo__name">SNOWCAST</p>
        <p className="snowcast-logo__tagline">Snow-aware planning</p>
      </div>
    </div>
  );
}
