import { useMemo } from 'react';
import type { ComponentType, ReactNode } from 'react';
import type { CriteriaConfig, DisplayMetadata, FiltersState, ResultsDisplay } from '../types';
import { normalize, resolvePath } from '../utils/dataAccess';

type PageInfo = {
  limit: number;
  offset: number;
  returned: number;
  total: number;
  hasNextPage: boolean;
  hasPrevPage: boolean;
};

type Props = {
  items: Record<string, any>[];
  totalCount: number;
  pageInfo?: PageInfo;
  debugMeta?: Record<string, unknown>;
  sectionOrder?: string[];
  selectedOrder?: Record<string, string[]>;
  filters?: FiltersState;
  isLoading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  onPageChange?: (page: number) => void;
  renderItem?: ComponentType<McdaResultCardProps>;
  display: ResultsDisplay;
  sections: CriteriaConfig[];
};

const SECTION_DOMINANCE_BASE = 5;
const VALUE_DECAY = 0.65;
const HIGH_PRIORITY_VALUE_WEIGHT_THRESHOLD = 0.5;

const renderTemplate = (template: string, item: Record<string, any>) =>
  template.replace(/\{([^}]+)\}/g, (_, path) => {
    const value = resolvePath(item, path.trim());
    if (value === undefined || value === null) return '';
    return String(value);
  });

const stripHtml = (value: string) => value.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

const TEXT_SEARCH_FIELDS = [
  'system_type',
  'scanner_reader',
  'phone_models',
  'scan_required',
  'scan_required_for_current_reading',
  'pricing_notes',
  'insurance_notes',
  'product_name',
  'notes'
];

const pushValue = (bucket: string[], value: unknown) => {
  if (value === null || value === undefined) return;
  if (Array.isArray(value)) {
    value.forEach((entry) => pushValue(bucket, entry));
    return;
  }
  if (typeof value === 'object') {
    Object.values(value as Record<string, unknown>).forEach((entry) => pushValue(bucket, entry));
    return;
  }
  bucket.push(String(value));
};

const buildTextSearchHaystack = (item: Record<string, any>) => {
  const parts: string[] = [];
  TEXT_SEARCH_FIELDS.forEach((path) => {
    const value = resolvePath(item, path);
    pushValue(parts, value);
  });
  const pricingSources = resolvePath(item, 'pricing_sources');
  if (Array.isArray(pricingSources)) {
    pricingSources.forEach((source) => {
      if (source && typeof source === 'object') {
        pushValue(parts, (source as Record<string, unknown>).label);
      }
    });
  }
  const scanRequired = resolvePath(item, 'scan_required');
  if (typeof scanRequired === 'string') {
    if (normalize(scanRequired) === 'no') parts.push('no scanning');
    if (normalize(scanRequired) === 'yes') parts.push('scan required');
  } else if (typeof scanRequired === 'boolean') {
    parts.push(scanRequired ? 'scan required' : 'no scanning');
  }
  const scanRequiredForReading = resolvePath(item, 'scan_required_for_current_reading');
  if (typeof scanRequiredForReading === 'boolean') {
    parts.push(scanRequiredForReading ? 'scan required' : 'no scanning');
  }
  return normalize(stripHtml(parts.join(' ')));
};

const canonicalSectionWeight = (totalSections: number, index: number) => {
  const dominancePower = Math.max(0, totalSections - index - 1);
  return Math.pow(SECTION_DOMINANCE_BASE, dominancePower);
};

const canonicalValueWeight = (rank: number) => Math.pow(VALUE_DECAY, rank);

type PrioritySpec = {
  sections: string[];
  selectedValues: Record<string, string[]>;
  tokenWeights: Map<string, number>;
  sectionWeights: Map<string, number>;
  selectedTokens: Set<string>;
  highPriorityTokens: Set<string>;
  totalSelectedCount: number;
};

const buildPrioritySpec = (
  sectionOrder: string[] = [],
  selectedOrder: Record<string, string[] | undefined> = {},
  rangeSelections: Set<string> = new Set()
): PrioritySpec => {
  const sections: string[] = [];
  const selectedValues: Record<string, string[]> = {};
  const tokenWeights = new Map<string, number>();
  const sectionWeights = new Map<string, number>();
  const selectedTokens = new Set<string>();
  const highPriorityTokens = new Set<string>();
  let totalSelectedCount = 0;
  const totalSections = sectionOrder.length;

  sectionOrder.forEach((sectionKey, sectionIndex) => {
    const normalizedSection = normalize(sectionKey);
    if (!normalizedSection) return;
    const rawItems = selectedOrder[sectionKey] ?? selectedOrder[normalizedSection];
    const items = Array.isArray(rawItems) ? (rawItems as string[]) : [];
    const normalizedItems: string[] = [];
    const seen = new Set<string>();
    items.forEach((item) => {
      const normalizedItem = normalize(item ?? '');
      if (!normalizedItem || seen.has(normalizedItem)) return;
      seen.add(normalizedItem);
      normalizedItems.push(normalizedItem);
    });

    const hasRange = rangeSelections.has(sectionKey);
    if (normalizedItems.length === 0 && !hasRange) {
      return;
    }

    sections.push(sectionKey);
    if (normalizedItems.length > 0) {
      selectedValues[sectionKey] = normalizedItems;
      totalSelectedCount += normalizedItems.length;
    } else {
      totalSelectedCount += 1;
    }

    const sectionWeight = canonicalSectionWeight(totalSections, sectionIndex);
    sectionWeights.set(sectionKey, sectionWeight);
    normalizedItems.forEach((value, valueIndex) => {
      const valueWeight = canonicalValueWeight(valueIndex);
      const token = `${sectionKey}:${value}`;
      tokenWeights.set(token, sectionWeight * valueWeight);
      selectedTokens.add(token);
      if (valueWeight >= HIGH_PRIORITY_VALUE_WEIGHT_THRESHOLD) {
        highPriorityTokens.add(token);
      }
    });
  });

  return {
    sections,
    selectedValues,
    tokenWeights,
    sectionWeights,
    selectedTokens,
    highPriorityTokens,
    totalSelectedCount
  };
};

const extractTokens = (item: Record<string, any>, section: CriteriaConfig) => {
  const sectionType = section.type || 'scalar';
  const path = section.path;
  const allowCustom = Boolean(section.allow_custom);
  const value = resolvePath(item, path);

  if (sectionType === 'scalar' || sectionType === 'match_any' || sectionType === 'checkboxes') {
    if (Array.isArray(value)) {
      return value
        .map((entry) => normalize(entry))
        .filter(Boolean)
        .map((normalizedValue) => `${section.key}:${normalizedValue}`);
    }
    const normalizedValue = normalize(value);
    return normalizedValue ? [`${section.key}:${normalizedValue}`] : [];
  }

  if (sectionType === 'array') {
    if (!Array.isArray(value)) return [];
    return value
      .map((entry) => normalize(entry))
      .filter(Boolean)
      .map((normalizedValue) => `${section.key}:${normalizedValue}`);
  }

  if (sectionType === 'boolean' || sectionType === 'toggle') {
    if (value === null || value === undefined) return [];
    return [`${section.key}:${value ? 'true' : 'false'}`];
  }

  if (allowCustom) {
    const normalizedValue = normalize(value);
    return normalizedValue ? [`${section.key}:${normalizedValue}`] : [];
  }

  return [];
};

const formatMetadataValue = (item: Record<string, any>, entry: DisplayMetadata) => {
  const raw = entry.path ? resolvePath(item, entry.path) : null;

  if (raw === null || raw === undefined) {
    if (entry.paths) {
      const values = entry.paths
        .map((path: string) => resolvePath(item, path))
        .filter((value: unknown): value is string | number => value !== undefined && value !== null);
      return values.join(', ');
    }
    return '—';
  }

  if (entry.format === 'currency') {
    const formatter = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: entry.currency || 'USD',
      maximumFractionDigits: 0
    });
    return formatter.format(Number(raw));
  }

  if (entry.format === 'date') {
    const date = new Date(String(raw));
    if (Number.isNaN(date.getTime())) return String(raw);
    return date.toLocaleDateString('en-US');
  }

  const value = String(raw);
  return entry.suffix ? `${value}${entry.suffix}` : value;
};

const formatMatchBadge = (score: number | undefined, topScore: number) => {
  if (!topScore || !score) return 'Match Score: —';
  if (score === topScore) return 'Priority Pick';
  const pct = Math.floor((score / topScore) * 100);
  if (pct >= 90) return `Strong Match: ${pct}%`;
  if (pct >= 80) return `Close Match: ${pct}%`;
  return `Match Score: ${Math.max(1, Math.min(99, pct))}%`;
};

export type McdaResultCardProps = {
  item: Record<string, any>;
  badgeLabel: string;
  scoreLabel: string | number;
  derivedScore: number;
  totalMatches: number;
  highPriorityMatches: number;
  rangeMatches: number;
  totalSelectedCount: number;
  display: ResultsDisplay;
};

export default function McdaItemList({
  items,
  totalCount,
  pageInfo,
  debugMeta,
  sectionOrder = [],
  selectedOrder = {},
  filters = {},
  isLoading = false,
  error = null,
  onRetry,
  onPageChange,
  renderItem,
  display,
  sections
}: Props) {
  const rangeSelections = useMemo(() => {
    const selections = new Map<string, { min: number | null; max: number | null }>();
    sections.forEach((section) => {
      if (section.type !== 'range') return;
      const raw = filters[section.key];
      if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return;
      const range = raw as Record<string, unknown>;
      const min = typeof range.min === 'number' ? (range.min as number) : null;
      const max = typeof range.max === 'number' ? (range.max as number) : null;
      if (min === null && max === null) return;
      selections.set(section.key, { min, max });
    });
    return selections;
  }, [sections, filters]);

  const prioritySpec = useMemo(
    () => buildPrioritySpec(sectionOrder, selectedOrder, new Set(rangeSelections.keys())),
    [sectionOrder, selectedOrder, rangeSelections]
  );
  const {
    sections: prioritySectionKeys,
    selectedValues,
    tokenWeights,
    sectionWeights,
    selectedTokens,
    highPriorityTokens,
    totalSelectedCount
  } = prioritySpec;
  const sectionMap = useMemo(() => {
    const map: Record<string, CriteriaConfig> = {};
    sections.forEach((section) => (map[section.key] = section));
    return map;
  }, [sections]);
  const searchTermSections = useMemo(
    () =>
      sections.filter(
        (section) =>
          section.ui === 'search_terms' ||
          section.ui === 'search_term_item' ||
          section.type === 'search_terms'
      ),
    [sections]
  );
  const prioritySectionSet = useMemo(() => new Set(prioritySectionKeys), [prioritySectionKeys]);
  const prioritySections = useMemo(
    () =>
      prioritySectionKeys
        .map((key) => sectionMap[key])
        .filter((section): section is CriteriaConfig => Boolean(section))
        .filter(
          (section) =>
            !(
              section.ui === 'search_terms' ||
              section.ui === 'search_term_item' ||
              section.type === 'search_terms'
            )
        ),
    [prioritySectionKeys, sectionMap]
  );
  const prioritySearchSections = useMemo(
    () => searchTermSections.filter((section) => prioritySectionSet.has(section.key)),
    [searchTermSections, prioritySectionSet]
  );

  const scoredItems = useMemo(() => {
    const sectionMap = new Map(sections.map((section) => [section.key, section]));
    const scored = items.map((item, index) => {
      const itemTokens = new Set<string>();
      prioritySections.forEach((section) => {
        extractTokens(item, section).forEach((token) => itemTokens.add(token));
      });
      prioritySearchSections.forEach((section) => {
        const haystack = buildTextSearchHaystack(item);
        const terms = selectedValues[section.key] || [];
        terms.forEach((term) => {
          if (!term) return;
          if (haystack.includes(term)) {
            itemTokens.add(`${section.key}:${term}`);
          }
        });
      });

      let totalMatches = 0;
      let highPriorityMatches = 0;
      let derivedScore = 0;
      let rangeMatches = 0;
      itemTokens.forEach((token) => {
        if (selectedTokens.has(token)) {
          totalMatches += 1;
          if (highPriorityTokens.has(token)) highPriorityMatches += 1;
          derivedScore += tokenWeights.get(token) ?? 0;
        }
      });

      if (rangeSelections.size > 0) {
        rangeSelections.forEach((range, sectionKey) => {
          const section = sectionMap.get(sectionKey);
          if (!section?.path) return;
          const rawValue = resolvePath(item, section.path);
          const numericValue = Number(rawValue);
          if (Number.isNaN(numericValue)) return;
          if (range.min !== null && numericValue < range.min) return;
          if (range.max !== null && numericValue > range.max) return;
          totalMatches += 1;
          highPriorityMatches += 1;
          rangeMatches += 1;
          derivedScore += sectionWeights.get(sectionKey) ?? 0;
        });
      }

      return { item, totalMatches, highPriorityMatches, derivedScore, rangeMatches, index };
    });
    if (totalSelectedCount > 0) {
      return [...scored].sort((a, b) => b.derivedScore - a.derivedScore || a.index - b.index);
    }
    return scored;
  }, [
    items,
    sectionOrder,
    prioritySections,
    prioritySearchSections,
    selectedTokens,
    highPriorityTokens,
    tokenWeights,
    rangeSelections,
    sectionWeights,
    selectedValues,
    totalSelectedCount
  ]);

  const topScore = scoredItems.reduce((max, entry) => Math.max(max, entry.derivedScore), 0);

  const currentPage = pageInfo ? Math.floor(pageInfo.offset / pageInfo.limit) + 1 : 1;
  const totalPages = pageInfo ? Math.max(1, Math.ceil(pageInfo.total / pageInfo.limit)) : 1;

  if (isLoading) {
    return (
      <div className="mcda-results">
        <h2 className="mcda-results-title">Results</h2>
        <div className="mcda-results-state">Loading listings…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mcda-results">
        <div className="mcda-results-error">
          <p>Having trouble reaching the server.</p>
          {onRetry && (
            <button onClick={onRetry} className="mcda-button mcda-button--ghost">
              Try again
            </button>
          )}
        </div>
      </div>
    );
  }

  if (!items.length) {
    return (
      <div className="mcda-results">
        <h2 className="mcda-results-title">Results</h2>
        <p className="mcda-results-empty">No listings found. Adjust your priorities or filters and try again.</p>
      </div>
    );
  }

  return (
    <div className="mcda-results">
      <div className="mcda-results-header">
        <h2 className="mcda-results-title">Results</h2>
        <div className="mcda-results-count">
          Showing {items.length} of {totalCount} listings
          {pageInfo && pageInfo.hasNextPage ? ' • more available' : ''}
        </div>
      </div>

      {debugMeta && (
        <details className="mcda-debug">
          <summary>Debug scoring payload</summary>
          <pre>{JSON.stringify(debugMeta, null, 2)}</pre>
        </details>
      )}

      <div className="mcda-results-list">
      {scoredItems.map(({ item, totalMatches, highPriorityMatches, derivedScore, rangeMatches }) => {
        const badgeLabel = formatMatchBadge(derivedScore, topScore);
        const scorePct =
          totalSelectedCount > 0 && topScore > 0 ? Math.round((derivedScore / topScore) * 100) : null;
        const scoreLabel = scorePct !== null ? `${scorePct}%` : '—';
        const cardProps: McdaResultCardProps = {
          item,
          badgeLabel,
          scoreLabel,
          derivedScore,
          totalMatches,
          highPriorityMatches,
          rangeMatches,
          totalSelectedCount,
          display
        };

          if (renderItem) {
            const RenderItem = renderItem;
            return (
              <div key={item.id ?? item.item_id}>
                <RenderItem {...cardProps} />
              </div>
            );
          }
          const metadataEntries = display.metadata ?? [];
          const priceEntry = metadataEntries[0];
          const extraMetadata = metadataEntries.slice(1);
          const title = display.title_template ? renderTemplate(display.title_template, item) : item.title || item.id;
          const subtitle = display.subtitle_template ? renderTemplate(display.subtitle_template, item).trim() : '';
          const imageSrc =
            resolvePath(item, display.image_path) ||
            display.empty_image ||
            'https://via.placeholder.com/640x480?text=Listing';

          return (
            <article key={item.id} className="mcda-result-card">
              <div className="mcda-result-grid">
                <div className="mcda-result-media">
                  <div className="mcda-result-image">
                    <img src={imageSrc} alt={title} loading="lazy" />
                    <div className="mcda-badge">
                      <span className="mcda-badge-icon">✓</span>
                      {badgeLabel}
                      <div className="mcda-badge-tooltip">
                        <p className="mcda-badge-title">Match insight</p>
                        <p>
                          This item hits <strong>{highPriorityMatches}</strong> of your top priorities.
                        </p>
                        <p>
                          Overall matches: <strong>{totalMatches}</strong> of {totalSelectedCount}
                        </p>
                        {rangeMatches > 0 && (
                          <p>
                            Range matches: <strong>{rangeMatches}</strong>
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mcda-result-content">
                  <div className="mcda-result-header">
                    <div>
                      <h3>{title}</h3>
                      {subtitle && <p className="mcda-result-subtitle">{subtitle}</p>}
                    </div>
                    <div className="mcda-result-price">
                      <p>{priceEntry ? formatMetadataValue(item, priceEntry) : '—'}</p>
                      <span>Score: {scoreLabel}</span>
                    </div>
                  </div>

                  {extraMetadata.length > 0 && (
                    <dl className="mcda-metadata-grid">
                      {extraMetadata.map((entry) => (
                        <div key={entry.label}>
                          <dt>{entry.label}</dt>
                          <dd>{formatMetadataValue(item, entry)}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                </div>
              </div>
            </article>
          );
        })}
      </div>

      {pageInfo && totalPages > 1 && (
        <div className="mcda-pagination">
          <button
            type="button"
            className="mcda-button mcda-button--ghost"
            disabled={!pageInfo.hasPrevPage || !onPageChange}
            onClick={() => onPageChange?.(Math.max(1, currentPage - 1))}
          >
            Prev
          </button>
          <span>
            Page {currentPage} of {totalPages}
          </span>
          <button
            type="button"
            className="mcda-button"
            disabled={!pageInfo.hasNextPage || !onPageChange}
            onClick={() => onPageChange?.(Math.min(totalPages, currentPage + 1))}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
