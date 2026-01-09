import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import type { McdaResultCardProps } from '../McdaItemList';

const formatCurrency = (value: number | null | undefined, currency = 'CAD') => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0
  }).format(Number(value));
};

const buildImageList = (item: Record<string, any>) => {
  const images = Array.isArray(item.images) ? item.images : [];
  const single = typeof item.image === 'string' ? [item.image] : [];
  const cleaned = [...images, ...single].filter((src) => typeof src === 'string' && src.length > 0);
  return cleaned.length > 0 ? cleaned : ['/assets/insulin/device-sensor.svg'];
};

export default function InsulinDevicesResultCard({
  item,
  badgeLabel,
  scoreLabel,
  totalMatches,
  highPriorityMatches,
  rangeMatches,
  totalSelectedCount
}: McdaResultCardProps) {
  const title = item.product_name || item.title || `Device ${item.id ?? ''}`;
  const manufacturer = item.manufacturer || '—';
  const systemType = item.system_type || '—';
  const scanRequired = item.scan_required || (item.scan_required_for_current_reading ? 'Yes' : 'No');
  const implantType = item.implant_type || (item.longwear_implant ? 'Implantable' : 'Wearable');
  const transmitterType = item.transmitter_type || (item.transmitter_is_sensor ? 'Integrated sensor' : 'Separate transmitter');
  const integrationType = item.integration_type || (item.mandatory_pump ? 'Pump-integrated' : 'Standalone CGM');
  const wearDays = typeof item.sensor_wear_duration_days === 'number' ? item.sensor_wear_duration_days : null;
  const warmupMinutes = typeof item.warmup_minutes === 'number' ? item.warmup_minutes : null;
  const initialEstimate =
    typeof item.estimated_initial_cost_cad === 'number'
      ? item.estimated_initial_cost_cad
      : typeof item.initial_cost_cad === 'number'
        ? item.initial_cost_cad
        : null;
  const monthlyEstimate =
    typeof item.estimated_monthly_cost_cad === 'number'
      ? item.estimated_monthly_cost_cad
      : typeof item.monthly_estimate_cad === 'number'
        ? item.monthly_estimate_cad
        : item.price_cad_ballpark?.monthly_estimate;
  const phoneModels = Array.isArray(item.phone_models) ? item.phone_models : [];
  const phonePlatforms = Array.isArray(item.phone_platforms) ? item.phone_platforms : [];
  const phoneList = phoneModels.length > 0 ? phoneModels : phonePlatforms;
  const phoneLabel =
    phoneList.length > 3
      ? `${phoneList.slice(0, 3).join(', ')} +${phoneList.length - 3} more`
      : phoneList.length > 0
        ? phoneList.join(', ')
        : '—';
  const insuranceNotes = item.insurance_notes;
  const pricingNotes = item.pricing_notes;
  const pricingSources = Array.isArray(item.pricing_sources) ? item.pricing_sources : [];
  const infoUrl = item.official_info_url;
  const showScore = totalSelectedCount > 0;

  const images = useMemo(() => buildImageList(item), [item]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [isLightboxOpen, setIsLightboxOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    setActiveIndex(0);
  }, [item.id]);

  useEffect(() => {
    if (!isLightboxOpen || typeof document === 'undefined') return;
    const { body } = document;
    const previousOverflow = body.style.overflow;
    body.style.overflow = 'hidden';
    return () => {
      body.style.overflow = previousOverflow;
    };
  }, [isLightboxOpen]);

  const activeImage = images[Math.min(activeIndex, images.length - 1)];
  const showControls = images.length > 1;

  const chips = [
    wearDays ? `${wearDays}-day wear` : null,
    scanRequired === 'Yes' ? 'Scan required' : 'No scanning',
    integrationType
  ].filter(Boolean) as string[];

  return (
    <article className="mcda-result-card insulin-card">
      <div className="insulin-card-grid">
        <div className="insulin-card-media">
          <div className="insulin-card-carousel">
            <button
              type="button"
              className="insulin-card-zoom"
              onClick={() => setIsLightboxOpen(true)}
              aria-label={`Enlarge image ${activeIndex + 1} of ${images.length}`}
            >
              <img src={activeImage} alt={`${title} image ${activeIndex + 1}`} loading="lazy" />
            </button>
            <div className="mcda-badge insulin-badge">
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
            {showControls && (
              <div className="insulin-card-controls">
                <button
                  type="button"
                  className="insulin-card-control"
                  onClick={() => setActiveIndex((prev) => (prev - 1 + images.length) % images.length)}
                  aria-label="View previous image"
                >
                  Prev
                </button>
                <button
                  type="button"
                  className="insulin-card-control"
                  onClick={() => setActiveIndex((prev) => (prev + 1) % images.length)}
                  aria-label="View next image"
                >
                  Next
                </button>
              </div>
            )}
          </div>

          {showControls && (
            <div className="insulin-card-thumbs">
              {images.map((src, index) => (
                <button
                  key={`${src}-${index}`}
                  type="button"
                  className={
                    index === activeIndex
                      ? 'insulin-card-thumb insulin-card-thumb--active'
                      : 'insulin-card-thumb'
                  }
                  onClick={() => setActiveIndex(index)}
                  aria-label={`View image ${index + 1}`}
                  aria-current={index === activeIndex}
                >
                  <img src={src} alt="" loading="lazy" />
                </button>
              ))}
            </div>
          )}

          {chips.length > 0 && (
            <div className="insulin-card-tags">
              {chips.map((chip) => (
                <span key={chip} className="insulin-card-chip">
                  {chip}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="insulin-card-body">
          <div className="insulin-card-header">
            <div>
              <h3>{title}</h3>
              <p className="insulin-card-subtitle">
                {manufacturer} · {systemType}
              </p>
            </div>
            <div className="insulin-card-price">
              <div className="insulin-card-price-block">
                <p>{formatCurrency(initialEstimate, 'CAD')}</p>
                <span>Est. initial</span>
              </div>
              <div className="insulin-card-price-block">
                <p>{formatCurrency(monthlyEstimate, 'CAD')}</p>
                <span>Est. monthly</span>
                {showScore && <span className="insulin-card-price-sub">Score {scoreLabel}</span>}
              </div>
            </div>
          </div>

          <dl className="insulin-card-meta">
            <div>
              <dt>Wear duration</dt>
              <dd>{wearDays ? `${wearDays} days` : '—'}</dd>
            </div>
            <div>
              <dt>Warm-up</dt>
              <dd>{warmupMinutes ? `${warmupMinutes} min` : '—'}</dd>
            </div>
            <div>
              <dt>Scan required</dt>
              <dd>{scanRequired}</dd>
            </div>
            <div>
              <dt>Sensor placement</dt>
              <dd>{implantType}</dd>
            </div>
            <div>
              <dt>Transmitter</dt>
              <dd>{transmitterType}</dd>
            </div>
            <div>
              <dt>Phone</dt>
              <dd>{phoneLabel}</dd>
            </div>
          </dl>

          {isExpanded && (
            <div className="insulin-card-details">
              {typeof pricingNotes === 'string' && pricingNotes.trim().length > 0 && (
                <p className="insulin-card-notes">{pricingNotes}</p>
              )}
              {typeof insuranceNotes === 'string' && insuranceNotes.trim().length > 0 && (
                <p className="insulin-card-notes">{insuranceNotes}</p>
              )}
              {pricingSources.length > 0 && (
                <ul className="insulin-card-sources">
                  {pricingSources.map((source: Record<string, any>) => (
                    <li key={source.url ?? source.label}>
                      {source.url ? (
                        <a href={source.url} target="_blank" rel="noreferrer">
                          {source.label ?? source.url}
                        </a>
                      ) : (
                        <span>{source.label ?? 'Source'}</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <div className="insulin-card-actions">
            {infoUrl && (
              <a className="insulin-card-link" href={infoUrl} target="_blank" rel="noreferrer">
                Official device details
              </a>
            )}
            <button
              type="button"
              className="insulin-card-link insulin-card-link--ghost"
              onClick={() => setIsExpanded((prev) => !prev)}
            >
              {isExpanded ? 'Hide details' : 'More details'}
            </button>
          </div>
        </div>
      </div>
      {isLightboxOpen && typeof document !== 'undefined'
        ? createPortal(
            <div
              className="insulin-lightbox"
              role="dialog"
              aria-modal="true"
              aria-label={`${title} enlarged images`}
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
                  <img src={activeImage} alt={`${title} image ${activeIndex + 1}`} />
                </div>
                {showControls && (
                  <div className="insulin-lightbox-controls">
                    <button
                      type="button"
                      className="insulin-card-control"
                      onClick={() =>
                        setActiveIndex((prev) => (prev - 1 + images.length) % images.length)
                      }
                      aria-label="View previous image"
                    >
                      Prev
                    </button>
                    <button
                      type="button"
                      className="insulin-card-control"
                      onClick={() => setActiveIndex((prev) => (prev + 1) % images.length)}
                      aria-label="View next image"
                    >
                      Next
                    </button>
                  </div>
                )}
                {showControls && (
                  <div className="insulin-lightbox-thumbs">
                    {images.map((src, index) => (
                      <button
                        key={`${src}-zoom-${index}`}
                        type="button"
                        className={
                          index === activeIndex
                            ? 'insulin-card-thumb insulin-card-thumb--active'
                            : 'insulin-card-thumb'
                        }
                        onClick={() => setActiveIndex(index)}
                        aria-label={`View image ${index + 1}`}
                        aria-current={index === activeIndex}
                      >
                        <img src={src} alt="" loading="lazy" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>,
            document.body
          )
        : null}
    </article>
  );
}
