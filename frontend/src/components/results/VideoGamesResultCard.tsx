import type { McdaResultCardProps } from '../McdaItemList';

const buildImageList = (item: Record<string, any>) => {
  const images: string[] = [];
  if (typeof item.image === 'string') images.push(item.image);
  if (Array.isArray(item.screenshots)) {
    item.screenshots.forEach((src: unknown) => {
      if (typeof src === 'string') images.push(src);
    });
  }
  return images.length > 0 ? images : ['/assets/octonotes.png'];
};

const formatRating = (mean: number | null | undefined) => {
  if (mean === null || mean === undefined || Number.isNaN(Number(mean))) return '—';
  return `${Math.round(Number(mean) * 100)}%`;
};

export default function VideoGamesResultCard({
  item,
  badgeLabel,
  scoreLabel,
  totalMatches,
  highPriorityMatches,
  rangeMatches,
  totalSelectedCount
}: McdaResultCardProps) {
  const title = item.name || item.title || `Game ${item.id ?? ''}`;
  const year = item.year ? String(item.year) : '—';
  const genre = item.genre || '—';
  const ratingMean = item.rating_mean ?? item.rating?.mean ?? null;
  const ratingCount = item.rating_count ?? item.rating?.count ?? null;
  const adultOnly = Boolean(item.adult_only);
  const arcade = Boolean(item.arcade_game);
  const platforms = Array.isArray(item.platform_names)
    ? item.platform_names
    : Array.isArray(item.platforms)
    ? item.platforms.map((platform: any) => platform?.name).filter(Boolean)
    : [];
  const platformLabel = platforms.length > 3 ? `${platforms.slice(0, 3).join(', ')} +${platforms.length - 3}` : platforms.join(', ');
  const link = item.link as string | undefined;
  const trailer = (item.micro_trailer || item.gameplay) as string | undefined;
  const screenshots = buildImageList(item);
  const hero = screenshots[0];

  return (
    <article className="mcda-result-card game-card">
      <div className="game-card-grid">
        <div className="game-card-media">
          <div className="game-card-hero">
            <img src={hero} alt={title} loading="lazy" />
            <div className="mcda-badge game-badge">
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
          {screenshots.length > 1 && (
            <div className="game-card-thumbs">
              {screenshots.slice(1, 5).map((src) => (
                <a key={src} href={src} target="_blank" rel="noreferrer" className="game-card-thumb">
                  <img src={src} alt={`${title} screenshot`} loading="lazy" />
                </a>
              ))}
            </div>
          )}
        </div>

        <div className="game-card-content">
          <div className="game-card-header">
            <div>
              <h3>{title}</h3>
              <p className="game-card-subtitle">{genre} • {year}</p>
            </div>
            <div className="game-card-score">
              <span className="game-card-rating">Rating {formatRating(ratingMean)}</span>
              {ratingCount ? <span className="game-card-rating-count">{ratingCount} reviews</span> : null}
              <span className="game-card-score-label">Score {scoreLabel}</span>
            </div>
          </div>

          <div className="game-card-meta">
            <div>
              <span className="game-card-label">Platforms</span>
              <span>{platformLabel || '—'}</span>
            </div>
            <div>
              <span className="game-card-label">Adult themes</span>
              <span>{adultOnly ? 'Yes' : 'No'}</span>
            </div>
            <div>
              <span className="game-card-label">Arcade</span>
              <span>{arcade ? 'Yes' : 'No'}</span>
            </div>
          </div>

          <div className="game-card-actions">
            {link && (
              <a className="mcda-button mcda-button--ghost" href={link} target="_blank" rel="noreferrer">
                View game
              </a>
            )}
            {trailer && (
              <a className="mcda-button" href={trailer} target="_blank" rel="noreferrer">
                Watch trailer
              </a>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}
