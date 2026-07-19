import {
  Search,
} from "lucide-react";
import type { FormEvent } from "react";

import { SnowcastLogo } from "../ui/SnowcastLogo";

export function SearchCommandHeader({
  brief,
  loading,
  onBriefChange,
  onSubmit,
  onSearch,
  onCurrentTrip,
}: {
  brief: string;
  loading: boolean;
  onBriefChange: (brief: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onSearch: () => void;
  onCurrentTrip: () => void;
}) {
  return (
    <header className="search-command-header">
      <div className="app-canvas search-command-header__inner">
        <button
          type="button"
          className="logo-button"
          aria-label="Go to search"
          onClick={onSearch}
        >
          <SnowcastLogo compact />
        </button>
        <form className="compact-search-form" onSubmit={onSubmit}>
          <label htmlFor="compact-trip-brief">Trip brief</label>
          <input
            id="compact-trip-brief"
            value={brief}
            onChange={(event) => onBriefChange(event.target.value)}
          />
          <button type="submit" aria-disabled={loading || undefined}>
            <Search aria-hidden="true" size={18} />
            {loading ? "Searching for trip options" : "Search trip options"}
          </button>
        </form>
        <nav aria-label="Primary navigation" className="compact-nav">
          <button type="button" aria-current="page" onClick={onSearch}>
            Search
          </button>
          <button type="button" onClick={onCurrentTrip}>
            Current trip
          </button>
        </nav>
      </div>
    </header>
  );
}
