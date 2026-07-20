export function TripEntityStack({
  destination,
  skiArea,
  stayBase,
  compact = false,
}: {
  destination: string;
  skiArea: string;
  stayBase: string;
  compact?: boolean;
}) {
  const items = [
    ["Destination", destination],
    ["Ski area", skiArea],
    ["Recommended place to stay", stayBase],
  ] as const;

  return (
    <dl
      className={`grid gap-3 ${
        compact ? "text-xs sm:grid-cols-3" : "text-sm sm:grid-cols-3"
      }`}
    >
      {items.map(([label, value]) => (
        <div key={label} className="min-w-0">
          <dt className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-muted">
            {label}
          </dt>
          <dd className="mt-1 truncate font-semibold text-ink">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
