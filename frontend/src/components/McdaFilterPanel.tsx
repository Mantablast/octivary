import React, { startTransition, useMemo, useState } from 'react';
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy
} from '@dnd-kit/sortable';
import type { CriteriaConfig, FiltersState } from '../types';
import SortableItem from './SortableItem';

type Props = {
  sections: CriteriaConfig[];
  filters: FiltersState;
  setFilters: React.Dispatch<React.SetStateAction<FiltersState>>;
  sectionOrder: string[];
  setSectionOrder: React.Dispatch<React.SetStateAction<string[]>>;
  selectedOrder: Record<string, string[]>;
  setSelectedOrder: React.Dispatch<React.SetStateAction<Record<string, string[]>>>;
  onSectionTouched?: (sectionKey: string) => void;
  description?: string;
};

const TOGGLE_ON = 'true';
const TOGGLE_OFF = 'false';

export default function McdaFilterPanel({
  sections,
  filters,
  setFilters,
  sectionOrder,
  setSectionOrder,
  selectedOrder,
  setSelectedOrder,
  onSectionTouched,
  description
}: Props) {
  const [searchInputs, setSearchInputs] = useState<Record<string, string>>({});
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});

  const sectionMap = useMemo(() => {
    const map: Record<string, CriteriaConfig> = {};
    sections.forEach((section) => {
      map[section.key] = section;
    });
    return map;
  }, [sections]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const toggleSection = (key: string) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const isChecked = (sectionKey: string, value: string) => {
    const current = selectedOrder[sectionKey] || [];
    return current.includes(value);
  };

  const isToggleSection = (section?: CriteriaConfig) =>
    section?.ui === 'toggle' || section?.type === 'boolean' || section?.type === 'toggle';

  const isRangeSection = (section?: CriteriaConfig) =>
    section?.ui === 'range' || section?.type === 'range';

  const isDropdownSection = (section?: CriteriaConfig) =>
    section?.ui === 'dropdown' || section?.type === 'dropdown';

  const isSearchTermsSection = (section?: CriteriaConfig) =>
    section?.ui === 'search_terms' || section?.type === 'search_terms';

  const toggleOption = (sectionKey: string, value: string) => {
    startTransition(() => {
      setSelectedOrder((prev) => {
        const current = prev[sectionKey] || [];
        const exists = current.includes(value);
        const next = exists ? current.filter((item) => item !== value) : [...current, value];
        return { ...prev, [sectionKey]: next };
      });

      setFilters((prev) => {
        const current = Array.isArray(prev[sectionKey]) ? [...(prev[sectionKey] as string[])] : [];
        const exists = current.includes(value);
        const next = exists ? current.filter((item) => item !== value) : [...current, value];
        return { ...prev, [sectionKey]: next };
      });
    });
  };

  const toggleSwitch = (sectionKey: string, enabled: boolean) => {
    onSectionTouched?.(sectionKey);
    startTransition(() => {
      setSelectedOrder((prev) => ({
        ...prev,
        [sectionKey]: enabled ? [TOGGLE_ON] : [TOGGLE_OFF]
      }));

      setFilters((prev) => ({
        ...prev,
        [sectionKey]: enabled
      }));
    });
  };

  const setDropdownValue = (sectionKey: string, value: string) => {
    startTransition(() => {
      setSelectedOrder((prev) => ({
        ...prev,
        [sectionKey]: value ? [value] : []
      }));

      setFilters((prev) => ({
        ...prev,
        [sectionKey]: value || null
      }));
    });
  };

  const addSearchTerm = (sectionKey: string, term: string) => {
    const normalized = term.trim();
    if (!normalized) return;
    onSectionTouched?.(sectionKey);
    startTransition(() => {
      setSelectedOrder((prev) => {
        const current = prev[sectionKey] || [];
        if (current.includes(normalized)) return prev;
        return { ...prev, [sectionKey]: [...current, normalized] };
      });

      setFilters((prev) => {
        const current = Array.isArray(prev[sectionKey]) ? [...(prev[sectionKey] as string[])] : [];
        if (current.includes(normalized)) return prev;
        return { ...prev, [sectionKey]: [...current, normalized] };
      });
    });
  };

  const removeSearchTerm = (sectionKey: string, term: string) => {
    onSectionTouched?.(sectionKey);
    startTransition(() => {
      setSelectedOrder((prev) => {
        const current = prev[sectionKey] || [];
        return { ...prev, [sectionKey]: current.filter((item) => item !== term) };
      });

      setFilters((prev) => {
        const current = Array.isArray(prev[sectionKey]) ? [...(prev[sectionKey] as string[])] : [];
        return { ...prev, [sectionKey]: current.filter((item) => item !== term) };
      });
    });
  };

  const hasRangeSelection = (sectionKey: string) => {
    const raw = filters[sectionKey];
    if (!raw || Array.isArray(raw) || typeof raw !== 'object') return false;
    const range = raw as Record<string, unknown>;
    const min = typeof range.min === 'number' ? range.min : null;
    const max = typeof range.max === 'number' ? range.max : null;
    return min !== null || max !== null;
  };

  const hasSelection = (sectionKey: string, section?: CriteriaConfig) => {
    if (isRangeSection(section)) {
      return hasRangeSelection(sectionKey);
    }
    if (isDropdownSection(section)) {
      const value = selectedOrder[sectionKey]?.[0];
      return Boolean(value);
    }
    if (isSearchTermsSection(section)) {
      const selected = selectedOrder[sectionKey] || [];
      return selected.length > 0;
    }
    const selected = selectedOrder[sectionKey] || [];
    return selected.length > 0;
  };

  return (
    <div className="mcda-panel">
      <p className="mcda-panel-desc">
        {description ||
          'Drag sections and checked values to tell Octivary what matters most. Higher items weigh more in ranking.'}
      </p>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={({ active, over }) => {
          if (!over) return;

          if (sectionOrder.includes(active.id as string)) {
            if (active.id !== over.id) {
              setSectionOrder((items) => {
                const oldIndex = items.indexOf(active.id as string);
                const newIndex = items.indexOf(over.id as string);
                return arrayMove(items, oldIndex, newIndex);
              });
            }
            onSectionTouched?.(active.id as string);
            return;
          }

          const [sectionKey, optionValue] = (active.id as string).split(':');
          const [, overValue] = (over.id as string).split(':');
          setSelectedOrder((prev) => {
            const current = prev[sectionKey] || [];
            if (!overValue) return prev;
            const oldIndex = current.indexOf(optionValue);
            const newIndex = current.indexOf(overValue);
            if (oldIndex < 0 || newIndex < 0) return prev;
            return {
              ...prev,
              [sectionKey]: arrayMove(current, oldIndex, newIndex)
            };
          });
        }}
      >
        <SortableContext items={sectionOrder} strategy={verticalListSortingStrategy}>
          {sectionOrder.map((sectionKey) => {
            const section = sectionMap[sectionKey];
            if (!section) return null;
            const selectedItems = selectedOrder[sectionKey] || [];
            const options = section.options || [];
            const isOpen = openSections[sectionKey];
            const titleClass = hasSelection(sectionKey, section)
              ? 'mcda-section-title mcda-section-title--active'
              : 'mcda-section-title';

            if (isToggleSection(section)) {
              const enabled = isChecked(sectionKey, TOGGLE_ON);
              return (
                <SortableItem key={sectionKey} id={sectionKey}>
                  {({ handleProps }) => (
                    <div className="mcda-section">
                      <div className="mcda-section-header">
                        <span
                          {...handleProps.attributes}
                          {...handleProps.listeners}
                          ref={handleProps.ref}
                          className="mcda-handle"
                          title="Drag section"
                        >
                          ☰
                        </span>
                        <span className={titleClass}>{section.label}</span>
                        <label className="mcda-switch">
                          <input
                            type="checkbox"
                            checked={enabled}
                            onChange={(event) => toggleSwitch(sectionKey, event.target.checked)}
                          />
                          <span className="mcda-switch-track" />
                          <span className="mcda-switch-thumb" />
                        </label>
                      </div>
                    </div>
                  )}
                </SortableItem>
              );
            }

            if (isDropdownSection(section)) {
              const selectedValue = selectedOrder[sectionKey]?.[0] ?? '';
              return (
                <SortableItem key={sectionKey} id={sectionKey}>
                  {({ handleProps }) => (
                    <div className="mcda-section">
                      <div className="mcda-section-header">
                        <span
                          {...handleProps.attributes}
                          {...handleProps.listeners}
                          ref={handleProps.ref}
                          className="mcda-handle"
                          title="Drag section"
                        >
                          ☰
                        </span>
                        <button type="button" className={titleClass} onClick={() => toggleSection(sectionKey)}>
                          {section.label}
                          <span className="mcda-chevron">{isOpen ? '▲' : '▼'}</span>
                        </button>
                      </div>
                      {isOpen && (
                        <div className="mcda-section-body">
                          <select
                            className="mcda-input"
                            value={selectedValue}
                            onChange={(event) => {
                              onSectionTouched?.(sectionKey);
                              setDropdownValue(sectionKey, event.target.value);
                            }}
                          >
                            <option value="">Select one…</option>
                            {options.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                    </div>
                  )}
                </SortableItem>
              );
            }

            if (isSearchTermsSection(section)) {
              const inputValue = searchInputs[sectionKey] ?? '';
              const placeholder = section.placeholder ?? 'Type a keyword...';
              return (
                <SortableItem key={sectionKey} id={sectionKey}>
                  {({ handleProps }) => (
                    <div className="mcda-section">
                      <div className="mcda-section-header">
                        <span
                          {...handleProps.attributes}
                          {...handleProps.listeners}
                          ref={handleProps.ref}
                          className="mcda-handle"
                          title="Drag section"
                        >
                          ☰
                        </span>
                        <button type="button" className={titleClass} onClick={() => toggleSection(sectionKey)}>
                          {section.label}
                          <span className="mcda-chevron">{isOpen ? '▲' : '▼'}</span>
                        </button>
                      </div>
                      {isOpen && (
                        <div className="mcda-section-body">
                          <div className="mcda-search-row">
                            <input
                              type="text"
                              className="mcda-input"
                              placeholder={placeholder}
                              value={inputValue}
                              onChange={(event) =>
                                setSearchInputs((prev) => ({ ...prev, [sectionKey]: event.target.value }))
                              }
                              onKeyDown={(event) => {
                                if (event.key !== 'Enter') return;
                                event.preventDefault();
                                addSearchTerm(sectionKey, inputValue);
                                setSearchInputs((prev) => ({ ...prev, [sectionKey]: '' }));
                              }}
                            />
                            <button
                              type="button"
                              className="mcda-button"
                              onClick={() => {
                                addSearchTerm(sectionKey, inputValue);
                                setSearchInputs((prev) => ({ ...prev, [sectionKey]: '' }));
                              }}
                            >
                              +
                            </button>
                          </div>

                          {selectedItems.length > 0 && (
                            <SortableContext
                              items={selectedItems.map((item) => `${sectionKey}:${item}`)}
                              strategy={verticalListSortingStrategy}
                            >
                              <div className="mcda-selected-list">
                                {selectedItems.map((item) => (
                                  <SortableItem key={`${sectionKey}:${item}`} id={`${sectionKey}:${item}`}>
                                    {({ handleProps }) => (
                                      <div className="mcda-selected-item">
                                        <span className="mcda-selected-label">{item}</span>
                                        <div className="mcda-selected-actions">
                                          <button
                                            type="button"
                                            className="mcda-link"
                                            onClick={() => removeSearchTerm(sectionKey, item)}
                                          >
                                            Remove
                                          </button>
                                          <span
                                            {...handleProps.attributes}
                                            {...handleProps.listeners}
                                            ref={handleProps.ref}
                                            className="mcda-handle mcda-handle--compact"
                                            title="Drag to reprioritize"
                                          >
                                            ☰
                                          </span>
                                        </div>
                                      </div>
                                    )}
                                  </SortableItem>
                                ))}
                              </div>
                            </SortableContext>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </SortableItem>
              );
            }

            if (isRangeSection(section)) {
              const raw = filters[sectionKey];
              const range =
                raw && typeof raw === 'object' && !Array.isArray(raw) ? (raw as Record<string, unknown>) : null;
              const minValue = typeof range?.min === 'number' ? (range.min as number) : '';
              const maxValue = typeof range?.max === 'number' ? (range.max as number) : '';
              return (
                <SortableItem key={sectionKey} id={sectionKey}>
                  {({ handleProps }) => (
                    <div className="mcda-section">
                      <div className="mcda-section-header">
                        <span
                          {...handleProps.attributes}
                          {...handleProps.listeners}
                          ref={handleProps.ref}
                          className="mcda-handle"
                          title="Drag section"
                        >
                          ☰
                        </span>
                        <button type="button" className={titleClass} onClick={() => toggleSection(sectionKey)}>
                          {section.label}
                          <span className="mcda-chevron">{isOpen ? '▲' : '▼'}</span>
                        </button>
                      </div>
                      {isOpen && (
                        <div className="mcda-section-body mcda-range-body">
                          <label className="mcda-range-row">
                            <span className="mcda-range-label">Min</span>
                            <div className="mcda-range-input">
                              <span className="mcda-range-prefix">$</span>
                              <input
                                type="number"
                                inputMode="numeric"
                                value={minValue}
                                min={0}
                                onChange={(event) => {
                                  const next = event.target.value;
                                  const parsed = next === '' ? null : Number(next);
                                  setFilters((prev) => {
                                    const current = prev[sectionKey];
                                    const base =
                                      current && typeof current === 'object' && !Array.isArray(current)
                                        ? { ...current }
                                        : {};
                                    return { ...prev, [sectionKey]: { ...base, min: parsed } };
                                  });
                                }}
                              />
                            </div>
                          </label>
                          <label className="mcda-range-row">
                            <span className="mcda-range-label">Max</span>
                            <div className="mcda-range-input">
                              <span className="mcda-range-prefix">$</span>
                              <input
                                type="number"
                                inputMode="numeric"
                                value={maxValue}
                                min={0}
                                onChange={(event) => {
                                  const next = event.target.value;
                                  const parsed = next === '' ? null : Number(next);
                                  setFilters((prev) => {
                                    const current = prev[sectionKey];
                                    const base =
                                      current && typeof current === 'object' && !Array.isArray(current)
                                        ? { ...current }
                                        : {};
                                    return { ...prev, [sectionKey]: { ...base, max: parsed } };
                                  });
                                }}
                              />
                            </div>
                          </label>
                        </div>
                      )}
                    </div>
                  )}
                </SortableItem>
              );
            }

            return (
              <SortableItem key={sectionKey} id={sectionKey}>
                {({ handleProps }) => (
                  <div className="mcda-section">
                    <div className="mcda-section-header">
                      <span
                        {...handleProps.attributes}
                        {...handleProps.listeners}
                        ref={handleProps.ref}
                        className="mcda-handle"
                        title="Drag section"
                      >
                        ☰
                      </span>
                      <button type="button" className={titleClass} onClick={() => toggleSection(sectionKey)}>
                        {section.label}
                        <span className="mcda-chevron">{isOpen ? '▲' : '▼'}</span>
                      </button>
                    </div>

                    {isOpen && (
                      <div className="mcda-section-body">
                        {selectedItems.length > 0 && (
                          <SortableContext
                            items={selectedItems.map((item) => `${sectionKey}:${item}`)}
                            strategy={verticalListSortingStrategy}
                          >
                            <div className="mcda-selected-list">
                              {selectedItems.map((item) => {
                                const option = options.find((opt) => opt.value === item);
                                return (
                                  <SortableItem key={`${sectionKey}:${item}`} id={`${sectionKey}:${item}`}>
                                    {({ handleProps: itemHandleProps }) => (
                                      <div className="mcda-selected-item">
                                        <input
                                          type="checkbox"
                                          checked
                                          onChange={() => toggleOption(sectionKey, item)}
                                        />
                                        <span className="mcda-selected-label">
                                          {option?.label ?? item}
                                        </span>
                                        <span
                                          {...itemHandleProps.attributes}
                                          {...itemHandleProps.listeners}
                                          ref={itemHandleProps.ref}
                                          className="mcda-handle mcda-handle--compact"
                                          title="Drag to reprioritize"
                                        >
                                          ☰
                                        </span>
                                      </div>
                                    )}
                                  </SortableItem>
                                );
                              })}
                            </div>
                          </SortableContext>
                        )}

                        <div className="mcda-option-list">
                          {options.length === 0 && (
                            <p className="mcda-help">No preset values configured.</p>
                          )}
                          {options
                            .filter((option) => !isChecked(sectionKey, option.value))
                            .map((option) => (
                              <label key={option.value} className="mcda-option-item">
                                <input
                                  type="checkbox"
                                  checked={false}
                                  onChange={() => toggleOption(sectionKey, option.value)}
                                />
                                {option.label}
                              </label>
                            ))}
                          {options.length > 0 &&
                            options.filter((option) => !isChecked(sectionKey, option.value)).length === 0 && (
                              <p className="mcda-help">All values selected—uncheck to remove from priorities.</p>
                            )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </SortableItem>
            );
          })}
        </SortableContext>
      </DndContext>
    </div>
  );
}
