import { useMemo } from 'react';
import type { ComponentType, ReactNode } from 'react';
import type { DisplayMetadata, ResultsDisplay } from '../types';
import { resolvePath } from '../utils/dataAccess';

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
  isLoading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  onPageChange?: (page: number) => void;
  perPage?: number;
  perPageOptions?: number[];
  onPerPageChange?: (perPage: number) => void;
  renderItem?: ComponentType<McdaResultCardProps>;
  display: ResultsDisplay;
};

const renderTemplate = (template: string, item: Record<string, any>) =>
  template.replace(/\{([^}]+)\}/g, (_, path) => {
    const value = resolvePath(item, path.trim());
    if (value === undefined || value === null) return '';
    return String(value);
  });

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
  isLoading = false,
  error = null,
  onRetry,
  onPageChange,
  perPage,
  perPageOptions,
  onPerPageChange,
  renderItem,
  display
}: Props) {
  const scoredItems = useMemo(
    () =>
      items.map((item, index) => {
        const mcda = item?._mcda || {};
        return {
          item,
          totalMatches: mcda.total_matches ?? 0,
          highPriorityMatches: mcda.high_priority_matches ?? 0,
          derivedScore: mcda.derived_score ?? 0,
          rangeMatches: mcda.range_matches ?? 0,
          index
        };
      }),
    [items]
  );

  const totalSelectedCount = useMemo(() => {
    const first = items.find((item) => item?._mcda);
    return typeof first?._mcda?.total_selected_count === 'number' ? first._mcda.total_selected_count : 0;
  }, [items]);

  const topScore = scoredItems.reduce((max, entry) => Math.max(max, entry.derivedScore), 0);

  const currentPage = pageInfo ? Math.floor(pageInfo.offset / pageInfo.limit) + 1 : 1;
  const totalPages = pageInfo ? Math.max(1, Math.ceil(pageInfo.total / pageInfo.limit)) : 1;
  const pageSize = pageInfo?.limit ?? perPage ?? 0;
  const canSelectPerPage = Boolean(onPerPageChange && perPageOptions && perPageOptions.length > 0);

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
        <div className="mcda-results-controls">
          <div className="mcda-results-count">
            Showing {items.length} of {totalCount} listings
            {pageInfo && pageInfo.hasNextPage ? ' • more available' : ''}
          </div>
          {canSelectPerPage && (
            <label className="mcda-results-per-page">
              Per page
              <select
                className="mcda-input"
                value={pageSize || perPageOptions?.[0] || 50}
                onChange={(event) => onPerPageChange?.(Number(event.target.value))}
              >
                {perPageOptions?.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          )}
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
