import type { McdaResultCardProps } from '../McdaItemList';
import { resolvePath } from '../../utils/dataAccess';

const formatPrice = (item: Record<string, any>) => {
  const price = item.price || {};
  if (price.display) return String(price.display);
  const amount = Number(price.amount);
  if (Number.isNaN(amount)) return '—';
  const currency = price.currency || item.listing_currency || 'USD';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2
  }).format(amount);
};

const formatDate = (value?: string) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

const pickShippingLabel = (shipping: Record<string, any>) => {
  if (shipping.free_expedited_shipping) return 'Free expedited';
  const rates = Array.isArray(shipping.rates) ? shipping.rates : [];
  const displays = rates
    .map((rate) => rate?.rate?.display)
    .filter((display) => typeof display === 'string') as string[];
  const freeRate = displays.find((display) => display.toUpperCase().includes('FREE'));
  if (freeRate) return 'Free shipping';
  if (displays.length > 0) return displays[0];
  return '—';
};

export default function ReverbAcousticGuitarsResultCard({
  item,
  badgeLabel,
  scoreLabel,
  totalMatches,
  highPriorityMatches,
  totalSelectedCount
}: McdaResultCardProps) {
  const title = item.title || `${item.make || ''} ${item.model || ''}`.trim() || `Listing ${item.id ?? ''}`;
  const imageSrc =
    resolvePath(item, 'photos[0]._links.large_crop.href') ||
    resolvePath(item, '_links.photo.href') ||
    '/assets/octonotes.png';
  const condition = item.condition?.display_name || '—';
  const year = item.year || '—';
  const finish = item.finish || '—';
  const seller = item.shop_name || '—';
  const published = item.published_at || item.created_at;
  const shipping = pickShippingLabel(item.shipping || {});
  const price = formatPrice(item);
  const categories = Array.isArray(item.categories) ? item.categories : [];
  const categoryLabels = categories
    .map((category) => category?.full_name)
    .filter((label) => typeof label === 'string')
    .slice(0, 2) as string[];
  const webUrl = item?._links?.web?.href;

  return (
    <article className="mcda-result-card reverb-card">
      <div className="reverb-card-grid">
        <div className="reverb-card-media">
          <div className="reverb-card-image">
            <img src={imageSrc} alt={title} loading="lazy" />
            <div className="mcda-badge reverb-badge">
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
          {categoryLabels.length > 0 && (
            <div className="reverb-card-tags">
              {categoryLabels.map((label) => (
                <span key={label} className="reverb-card-chip">
                  {label}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="reverb-card-body">
          <div className="reverb-card-header">
            <div>
              <h3>{title}</h3>
              <p className="reverb-card-subtitle">
                {item.make ? item.make : 'Unknown make'} · {item.model || 'Unknown model'} · {year}
              </p>
            </div>
            <div className="reverb-card-price">
              <p>{price}</p>
              <span>Score: {scoreLabel}</span>
            </div>
          </div>

          <dl className="reverb-card-meta">
            <div>
              <dt>Condition</dt>
              <dd>{condition}</dd>
            </div>
            <div>
              <dt>Finish</dt>
              <dd>{finish}</dd>
            </div>
            <div>
              <dt>Shipping</dt>
              <dd>{shipping}</dd>
            </div>
            <div>
              <dt>Seller</dt>
              <dd>{seller}</dd>
            </div>
            <div>
              <dt>Listed</dt>
              <dd>{formatDate(published)}</dd>
            </div>
          </dl>

          <div className="reverb-card-actions">
            {webUrl && (
              <a className="reverb-card-link" href={webUrl} target="_blank" rel="noreferrer">
                View on Reverb
              </a>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}
