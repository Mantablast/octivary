import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import type { McdaResultCardProps } from '../McdaItemList';
import type { DisplayMetadata } from '../../types';
import { resolvePath } from '../../utils/dataAccess';

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

  if (entry.format === 'date') {
    const date = new Date(String(raw));
    if (Number.isNaN(date.getTime())) return String(raw);
    return date.toLocaleDateString('en-US');
  }

  const value = String(raw);
  return entry.suffix ? `${value}${entry.suffix}` : value;
};

export default function BibleCatalogResultCard({
  item,
  badgeLabel,
  scoreLabel,
  totalMatches,
  highPriorityMatches,
  rangeMatches,
  totalSelectedCount,
  display
}: McdaResultCardProps) {
  const title = display.title_template ? renderTemplate(display.title_template, item) : item.title || item.id;
  const subtitle = display.subtitle_template ? renderTemplate(display.subtitle_template, item).trim() : '';
  const fallbackImage =
    resolvePath(item, display.image_path) ||
    display.empty_image ||
    '/assets/octonotes.png';
  const metadataEntries = display.metadata ?? [];
  const isbn13 = typeof item.isbn13 === 'string' ? item.isbn13 : '';
  const coverBase = isbn13 ? `https://covers.openlibrary.org/b/isbn/${isbn13}` : '';
  const mediumCover = coverBase ? `${coverBase}-M.jpg?default=false` : '';
  const largeCover = coverBase ? `${coverBase}-L.jpg?default=false` : '';
  const canCopy = Boolean(isbn13) && typeof navigator !== 'undefined' && Boolean(navigator.clipboard);
  const [copied, setCopied] = useState(false);
  const [imageSrc, setImageSrc] = useState(mediumCover || fallbackImage);
  const [zoomSrc, setZoomSrc] = useState(largeCover || fallbackImage);
  const [isLightboxOpen, setIsLightboxOpen] = useState(false);

  useEffect(() => {
    setImageSrc(mediumCover || fallbackImage);
    setZoomSrc(largeCover || fallbackImage);
    setIsLightboxOpen(false);
  }, [mediumCover, largeCover, fallbackImage, item.id]);

  const handleCopy = async () => {
    if (!canCopy) return;
    try {
      await navigator.clipboard.writeText(isbn13);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      setCopied(false);
    }
  };

  const handleCoverError = () => {
    if (imageSrc === fallbackImage) return;
    setImageSrc(fallbackImage);
    setZoomSrc(fallbackImage);
  };

  const handleZoomError = () => {
    if (zoomSrc === fallbackImage) return;
    setZoomSrc(fallbackImage);
  };

  return (
    <article className="mcda-result-card bible-card">
      <div className="mcda-result-grid">
        <div className="mcda-result-media">
          <div className="mcda-result-image">
            <button
              type="button"
              className="bible-card-zoom"
              onClick={() => setIsLightboxOpen(true)}
              aria-label="Zoom cover image"
            >
              <img src={imageSrc} alt={title} loading="lazy" onError={handleCoverError} />
            </button>
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
              <p>{item.publisher || '—'}</p>
              <span>Score: {scoreLabel}</span>
            </div>
          </div>

          <dl className="mcda-metadata-grid">
            <div>
              <dt>ISBN-13</dt>
              <dd>
                <span className="bible-card-isbn">
                  {isbn13 || '—'}
                  <button
                    type="button"
                    className={copied ? 'bible-copy-button bible-copy-button--copied' : 'bible-copy-button'}
                    onClick={handleCopy}
                    disabled={!canCopy}
                    aria-label="Copy ISBN-13"
                  >
                    <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
                      <path
                        d="M5 2.5C5 1.67 5.67 1 6.5 1h6C13.33 1 14 1.67 14 2.5v8c0 .83-.67 1.5-1.5 1.5h-6C5.67 12 5 11.33 5 10.5v-8Zm1.5-.5a.5.5 0 0 0-.5.5v8a.5.5 0 0 0 .5.5h6a.5.5 0 0 0 .5-.5v-8a.5.5 0 0 0-.5-.5h-6Zm-3 3A1.5 1.5 0 0 1 5 3.5v1H4v-1a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v9c0 .28.22.5.5.5h6a.5.5 0 0 0 .5-.5v-1h1v1a1.5 1.5 0 0 1-1.5 1.5h-6A1.5 1.5 0 0 1 1 12.5v-9A1.5 1.5 0 0 1 2.5 2h1Z"
                        fill="currentColor"
                      />
                    </svg>
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                </span>
              </dd>
            </div>
            {metadataEntries.map((entry) => (
              <div key={entry.label}>
                <dt>{entry.label}</dt>
                <dd>{formatMetadataValue(item, entry)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
      {isLightboxOpen && typeof document !== 'undefined'
        ? createPortal(
            <div
              className="insulin-lightbox"
              role="dialog"
              aria-modal="true"
              aria-label={`${title} enlarged cover`}
              onClick={(event) => {
                if (event.target === event.currentTarget) setIsLightboxOpen(false);
              }}
            >
              <div className="insulin-lightbox-panel">
                <button
                  type="button"
                  className="insulin-lightbox-close"
                  onClick={() => setIsLightboxOpen(false)}
                  aria-label="Close image viewer"
                >
                  Close
                </button>
                <div className="insulin-lightbox-media">
                  <img src={zoomSrc} alt={`${title} cover`} onError={handleZoomError} />
                </div>
              </div>
            </div>,
            document.body
          )
        : null}
    </article>
  );
}
