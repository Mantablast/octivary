import { useMemo } from 'react';
import type { ReactNode } from 'react';
import type { CriteriaConfig, DisplayMetadata, ResultsDisplay } from '../types';
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
  isLoading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  onPageChange?: (page: number) => void;
  renderItem?: (props: McdaResultCardProps) => ReactNode;
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

const canonicalSectionWeight = (totalSections: number, index: number) => {
  const dominancePower = Math.max(0, totalSections - index - 1);
  return Math.pow(SECTION_DOMINANCE_BASE, dominancePower);
};

const canonicalValueWeight = (rank: number) => Math.pow(VALUE_DECAY, rank);

type PrioritySpec = {
  sections: string[];
  selectedValues: Record<string, string[]>;
  tokenWeights: Map<string, number>;
  selectedTokens: Set<string>;
  highPriorityTokens: Set<string>;
  totalSelectedCount: number;
};

const buildPrioritySpec = (
  sectionOrder: string[] = [],
  selectedOrder: Record<string, string[] | undefined> = {}
): PrioritySpec => {
  const sections: string[] = [];
  const selectedValues: Record<string, string[]> = {};
  const tokenWeights = new Map<string, number>();
  const selectedTokens = new Set<string>();
  const highPriorityTokens = new Set<string>();
  let totalSelectedCount = 0;

  sectionOrder.forEach((sectionKey) => {
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
    if (normalizedItems.length === 0) return;
    sections.push(sectionKey);
    selectedValues[sectionKey] = normalizedItems;
    totalSelectedCount += normalizedItems.length;
  });

  const totalSections = sections.length;
  sections.forEach((sectionKey, sectionIndex) => {
    const sectionWeight = canonicalSectionWeight(totalSections, sectionIndex);
    const values = selectedValues[sectionKey] || [];
    values.forEach((value, valueIndex) => {
      const valueWeight = canonicalValueWeight(valueIndex);
      const token = `${sectionKey}:${value}`;
      tokenWeights.set(token, sectionWeight * valueWeight);
      selectedTokens.add(token);
      if (valueWeight >= HIGH_PRIORITY_VALUE_WEIGHT_THRESHOLD) {
        highPriorityTokens.add(token);
      }
    });
  });

  return { sections, selectedValues, tokenWeights, selectedTokens, highPriorityTokens, totalSelectedCount };
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
  isLoading = false,
  error = null,
  onRetry,
  onPageChange,
  renderItem,
  display,
  sections
}: Props) {
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

  const prioritySpec = useMemo(
    () => buildPrioritySpec(sectionOrder, selectedOrder),
    [sectionOrder, selectedOrder]
  );
  const {
    sections: prioritySectionKeys,
    selectedValues,
    tokenWeights,
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
    () => sections.filter((section) => section.ui === 'search_terms' || section.type === 'search_terms'),
    [sections]
  );
  const prioritySectionSet = useMemo(() => new Set(prioritySectionKeys), [prioritySectionKeys]);
  const prioritySections = useMemo(
    () =>
      prioritySectionKeys
        .map((key) => sectionMap[key])
        .filter((section): section is CriteriaConfig => Boolean(section))
        .filter((section) => !(section.ui === 'search_terms' || section.type === 'search_terms')),
    [prioritySectionKeys, sectionMap]
  );
  const prioritySearchSections = useMemo(
    () => searchTermSections.filter((section) => prioritySectionSet.has(section.key)),
    [searchTermSections, prioritySectionSet]
  );

  const scoredItems = useMemo(() => {
    const scored = items.map((item, index) => {
      const itemTokens = new Set<string>();
      prioritySections.forEach((section) => {
        extractTokens(item, section).forEach((token) => itemTokens.add(token));
      });
      prioritySearchSections.forEach((section) => {
        const raw = resolvePath(item, section.path);
        if (typeof raw !== 'string') return;
        const haystack = normalize(stripHtml(raw));
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
      itemTokens.forEach((token) => {
        if (selectedTokens.has(token)) {
          totalMatches += 1;
          if (highPriorityTokens.has(token)) highPriorityMatches += 1;
          derivedScore += tokenWeights.get(token) ?? 0;
        }
      });

      return { item, totalMatches, highPriorityMatches, derivedScore, index };
    });
    if (totalSelectedCount > 0) {
      return [...scored].sort((a, b) => b.derivedScore - a.derivedScore || a.index - b.index);
    }
    return scored;
  }, [
    items,
    prioritySections,
    prioritySearchSections,
    selectedTokens,
    highPriorityTokens,
    tokenWeights,
    selectedValues,
    totalSelectedCount
  ]);

  const topScore = scoredItems.reduce((max, entry) => Math.max(max, entry.derivedScore), 0);

  const currentPage = pageInfo ? Math.floor(pageInfo.offset / pageInfo.limit) + 1 : 1;
  const totalPages = pageInfo ? Math.max(1, Math.ceil(pageInfo.total / pageInfo.limit)) : 1;

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
        {scoredItems.map(({ item, totalMatches, highPriorityMatches, derivedScore }) => {
          const badgeLabel = formatMatchBadge(derivedScore, topScore);
          const scoreLabel = totalSelectedCount > 0 ? Math.round(derivedScore * 100) / 100 : '—';
          const cardProps: McdaResultCardProps = {
            item,
            badgeLabel,
            scoreLabel,
            derivedScore,
            totalMatches,
            highPriorityMatches,
            totalSelectedCount,
            display
          };

          if (renderItem) {
            return (
              <div key={item.id ?? item.item_id}>
                {renderItem(cardProps)}
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
