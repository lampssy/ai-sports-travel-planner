import { evidenceQualityCopy, type EvidenceQualityMode } from "./snowcastCopy";

const modeClasses: Record<EvidenceQualityMode, string> = {
  archiveBacked: "border-alpineBlue/18 bg-alpineBlue/10 text-alpineBlue",
  forecastAssisted: "border-pine/18 bg-pine/10 text-pine",
  fallbackHeavy: "border-amber/25 bg-amber/10 text-amber",
};

export function EvidenceQualityBadge({
  mode,
  seasons,
  compact = false,
}: {
  mode: EvidenceQualityMode;
  seasons?: number | null;
  compact?: boolean;
}) {
  const copy = evidenceQualityCopy[mode];

  return (
    <div
      className={`rounded-2xl border ${modeClasses[mode]} ${
        compact ? "px-3 py-2" : "px-4 py-3"
      }`}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.14em]">
        Evidence quality
      </p>
      <div className="mt-1 flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <p className="font-semibold text-ink">{copy.label}</p>
        {seasons !== null && seasons !== undefined ? (
          <span className="text-xs font-semibold">
            · {seasons} season{seasons === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>
      {!compact ? (
        <p className="mt-1 text-xs leading-5 text-muted">{copy.description}</p>
      ) : null}
    </div>
  );
}
