import {
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";

export interface SegmentedTab {
  id: string;
  label: ReactNode;
  panel: ReactNode;
}

export function SegmentedTabs({
  tabs,
  ariaLabel,
  defaultValue,
  value,
  onValueChange,
  className,
}: {
  tabs: readonly SegmentedTab[];
  ariaLabel: string;
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  className?: string;
}) {
  const instanceId = useId().replace(/:/g, "");
  const fallbackId = tabs[0]?.id ?? "";
  const [internalValue, setInternalValue] = useState(defaultValue ?? fallbackId);
  const requestedValue = value ?? internalValue;
  const selectedId = tabs.some((tab) => tab.id === requestedValue)
    ? requestedValue
    : fallbackId;
  const tabRefs = useRef(new Map<string, HTMLButtonElement>());

  const select = (id: string) => {
    if (value === undefined) {
      setInternalValue(id);
    }
    onValueChange?.(id);
  };

  const moveFocus = (id: string) => {
    select(id);
    tabRefs.current.get(id)?.focus();
  };

  const handleKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    focusedId: string,
  ) => {
    const currentIndex = tabs.findIndex((tab) => tab.id === focusedId);
    if (currentIndex < 0 || tabs.length === 0) {
      return;
    }

    let nextIndex: number | null = null;
    if (event.key === "ArrowRight") {
      nextIndex = (currentIndex + 1) % tabs.length;
    } else if (event.key === "ArrowLeft") {
      nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = tabs.length - 1;
    }

    if (nextIndex !== null) {
      event.preventDefault();
      moveFocus(tabs[nextIndex].id);
    }
  };

  if (tabs.length === 0) {
    return null;
  }

  return (
    <div className={`snowcast-segmented-tabs${className ? ` ${className}` : ""}`}>
      <div
        className="snowcast-segmented-tabs__list"
        role="tablist"
        aria-label={ariaLabel}
      >
        {tabs.map((tab, index) => {
          const selected = tab.id === selectedId;
          const tabId = `${instanceId}-tab-${index}`;
          const panelId = `${instanceId}-panel-${index}`;
          return (
            <button
              key={tab.id}
              ref={(node) => {
                if (node) {
                  tabRefs.current.set(tab.id, node);
                } else {
                  tabRefs.current.delete(tab.id);
                }
              }}
              type="button"
              id={tabId}
              role="tab"
              aria-selected={selected}
              aria-controls={panelId}
              tabIndex={selected ? 0 : -1}
              className="snowcast-segmented-tabs__tab"
              onClick={() => select(tab.id)}
              onKeyDown={(event) => handleKeyDown(event, tab.id)}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      {tabs.map((tab, index) => {
        const selected = tab.id === selectedId;
        return (
          <div
            key={tab.id}
            id={`${instanceId}-panel-${index}`}
            role="tabpanel"
            aria-labelledby={`${instanceId}-tab-${index}`}
            hidden={!selected}
            tabIndex={0}
            className="snowcast-segmented-tabs__panel"
          >
            {tab.panel}
          </div>
        );
      })}
    </div>
  );
}
