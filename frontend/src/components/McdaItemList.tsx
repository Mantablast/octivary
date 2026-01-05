import { useMemo } from 'react';
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
  display: ResultsDisplay;
  sections: CriteriaConfig[];
};

const VALUE_DECAY = 0.65;
const HIGH_PRIORITY_VALUE_WEIGHT_THRESHOLD = 0.5;

const renderTemplate = (template: string, item: Record<string, any>) =>
  template.replace(/\{([^}]+)\}/g, (_, path) => {
    const value = resolvePath(item, path.trim());
    if (value === undefined || value === null) return '';
    return String(value);
  });

const stripHtml = (value: string) => value.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

const buildSelectionTokens = (
  sectionOrder: string[] = [],
  selectedOrder: Record<string, string[] | undefined> = {}
) => {
  const highPriorityTokens = new Set<string>();
  const selectedTokens = new Set<string>();
  let totalSelectedCount = 0;

  sectionOrder.forEach((sectionKey) => {
    const key = normalize(sectionKey);
    if (!key) return;
    const rawItems = selectedOrder[sectionKey] ?? selectedOrder[key];
    const items = Array.isArray(rawItems) ? (rawItems as string[]) : [];
    items.forEach((item, index) => {
      const normalizedItem = normalize(item ?? '');
      if (!normalizedItem) return;
      const token = `${key}:${normalizedItem}`;
      selectedTokens.add(token);
      totalSelectedCount += 1;
      const valueWeight = Math.pow(VALUE_DECAY, index);
      if (valueWeight >= HIGH_PRIORITY_VALUE_WEIGHT_THRESHOLD) {
        highPriorityTokens.add(token);
      }
    });
  });

  return { selectedTokens, highPriorityTokens, totalSelectedCount };
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

  const selectionTokens = useMemo(
    () => buildSelectionTokens(sectionOrder, selectedOrder),
    [sectionOrder, selectedOrder]
  );
  const { selectedTokens, highPriorityTokens, totalSelectedCount } = selectionTokens;
  const sectionMap = useMemo(() => {
    const map: Record<string, CriteriaConfig> = {};
    sections.forEach((section) => (map[section.key] = section));
    return map;
  }, [sections]);
  const searchTermSections = useMemo(
    () => sections.filter((section) => section.ui === 'search_terms' || section.type === 'search_terms'),
    [sections]
  );

  const scoredItems = useMemo(() => {
    return items.map((item) => {
      const itemTokens = new Set<string>();
      Object.values(sectionMap).forEach((section) => {
        extractTokens(item, section).forEach((token) => itemTokens.add(token));
      });
      searchTermSections.forEach((section) => {
        const raw = resolvePath(item, section.path);
        if (typeof raw !== 'string') return;
        const haystack = normalize(stripHtml(raw));
        const selected = selectedOrder[section.key] || [];
        selected.forEach((term) => {
          const normalizedTerm = normalize(term);
          if (!normalizedTerm) return;
          if (haystack.includes(normalizedTerm)) {
            itemTokens.add(`${section.key}:${normalizedTerm}`);
          }
        });
      });

      let totalMatches = 0;
      let highPriorityMatches = 0;
      itemTokens.forEach((token) => {
        if (selectedTokens.has(token)) {
          totalMatches += 1;
          if (highPriorityTokens.has(token)) highPriorityMatches += 1;
        }
      });

      const derivedScore = typeof item.score === 'number' ? item.score : totalMatches;
      return { item, totalMatches, highPriorityMatches, derivedScore };
    });
  }, [items, sectionMap, selectedTokens, highPriorityTokens, searchTermSections, selectedOrder]);

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
          const scoreLabel = totalSelectedCount > 0 ? derivedScore : '—';
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
