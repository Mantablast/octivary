import { FormEvent, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import type { DynamicSearchJob } from '../types';

const POLL_INTERVAL_MS = 1200;
const RESULT_LIMIT = 12;

function buildHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    accept: 'application/json',
    'content-type': 'application/json'
  };
  const apiToken = (import.meta.env.VITE_API_TOKEN || '').trim();
  if (apiToken) {
    headers.Authorization = `Bearer ${apiToken}`;
  }
  return headers;
}

async function fetchJob(jobId: string): Promise<DynamicSearchJob> {
  const apiBase = (import.meta.env.VITE_API_BASE || '').trim();
  const response = await fetch(`${apiBase}/api/dynamic-search/jobs/${jobId}`, {
    headers: buildHeaders()
  });
  if (!response.ok) {
    throw new Error('Failed to load the current finder job.');
  }
  return response.json() as Promise<DynamicSearchJob>;
}

async function listJobs(): Promise<DynamicSearchJob[]> {
  const apiBase = (import.meta.env.VITE_API_BASE || '').trim();
  const response = await fetch(`${apiBase}/api/dynamic-search/jobs?limit=6`, {
    headers: buildHeaders()
  });
  if (!response.ok) {
    throw new Error('Failed to load recent finder jobs.');
  }
  return response.json() as Promise<DynamicSearchJob[]>;
}

export default function DynamicFinder() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = (searchParams.get('q') || '').trim();
  const [query, setQuery] = useState(initialQuery);
  const [job, setJob] = useState<DynamicSearchJob | null>(null);
  const [recentJobs, setRecentJobs] = useState<DynamicSearchJob[]>([]);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const hasAutoSubmitted = useRef(false);
  const hasAutoOpenedFilter = useRef(false);

  const loadRecentJobs = async () => {
    try {
      const jobs = await listJobs();
      setRecentJobs(jobs);
    } catch {
      // Keep the page usable even if history fails to load.
    }
  };

  useEffect(() => {
    loadRecentJobs();
  }, []);

  const submitQuery = async (rawQuery: string) => {
    const trimmed = rawQuery.trim();
    if (trimmed.length < 2) {
      setError('Enter at least two characters to build a comparison.');
      return;
    }

    setError('');
    setIsSubmitting(true);
    hasAutoOpenedFilter.current = false;
    try {
      const apiBase = (import.meta.env.VITE_API_BASE || '').trim();
      if (!apiBase) {
        throw new Error('API base is not configured. Set VITE_API_BASE to use the finder.');
      }
      const response = await fetch(`${apiBase}/api/dynamic-search/jobs`, {
        method: 'POST',
        headers: buildHeaders(),
        body: JSON.stringify({ query: trimmed, limit: RESULT_LIMIT })
      });
      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || 'Failed to create a finder job.');
      }
      const nextJob = (await response.json()) as DynamicSearchJob;
      setJob(nextJob);
      setSearchParams({ q: trimmed }, { replace: true });
      loadRecentJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create a finder job.');
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    if (!initialQuery || hasAutoSubmitted.current) {
      return;
    }
    const sessionKey = `octivary-finder-autosubmit:${initialQuery.toLowerCase()}`;
    if (window.sessionStorage.getItem(sessionKey) === '1') {
      return;
    }
    window.sessionStorage.setItem(sessionKey, '1');
    hasAutoSubmitted.current = true;
    submitQuery(initialQuery);
  }, [initialQuery]);

  useEffect(() => {
    if (!job || job.status === 'completed' || job.status === 'failed') {
      return;
    }

    let cancelled = false;
    let timer = 0;

    const poll = async () => {
      try {
        const nextJob = await fetchJob(job.job_id);
        if (cancelled) return;
        setJob(nextJob);
        if (nextJob.status === 'completed' || nextJob.status === 'failed') {
          loadRecentJobs();
          return;
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to poll the finder job.');
      }
      timer = window.setTimeout(poll, POLL_INTERVAL_MS);
    };

    timer = window.setTimeout(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [job]);

  useEffect(() => {
    if (!job || job.status !== 'completed' || hasAutoOpenedFilter.current) {
      return;
    }
    if (!job.result?.config_key || !job.result?.evidence_count) {
      return;
    }
    hasAutoOpenedFilter.current = true;
    navigate(`/filters/${job.result.config_key}?dynamicJob=${encodeURIComponent(job.job_id)}`, {
      replace: true
    });
  }, [job, navigate]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    submitQuery(query);
  };

  const progressWidth = `${Math.max(8, Math.round((job?.progress || 0) * 100))}%`;
  const result = job?.result;
  const showResults = Boolean(job);

  if (!showResults) {
    return (
      <section className="finder-landing">
        <form className="finder-launch" onSubmit={handleSubmit}>
          <input
            id="finder-query"
            className="finder-input finder-input--landing"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search any product"
            aria-label="Search any product"
          />
          <button className="cta finder-launch-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Building...' : 'Build'}
          </button>
        </form>
        {error ? <p className="finder-error">{error}</p> : null}
      </section>
    );
  }

  return (
    <section className="finder-page">
      <div className="finder-hero card">
        <form className="finder-form" onSubmit={handleSubmit}>
          <div className="finder-input-row">
            <input
              id="finder-query"
              className="finder-input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Dexcom G7, KJV study bible, Toyota Camry"
            />
            <button className="cta" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Building...' : 'Build'}
            </button>
          </div>
        </form>

        {error ? <p className="finder-error">{error}</p> : null}
      </div>

      <div className="finder-layout">
        <aside className="card finder-status-card">
          <div className="finder-status-header">
            <div>
              <p className="eyebrow">Job status</p>
              <h2>{job ? job.current_step : 'Waiting for a search'}</h2>
            </div>
            <span className={`status-pill status-${job?.status || 'idle'}`}>
              {job?.status || 'idle'}
            </span>
          </div>
          <div className="finder-progress">
            <div className="finder-progress-bar" style={{ width: progressWidth }} />
          </div>
          <p className="muted">
            {job
              ? `Profile: ${job.profile} · Query: ${job.query}`
              : 'Waiting for a build request.'}
          </p>
          {job?.error_message ? <p className="finder-error">{job.error_message}</p> : null}
          {result?.open_filter_path ? (
            <Link className="ghost-link" to={`${result.open_filter_path}?dynamicJob=${encodeURIComponent(job?.job_id || '')}`}>
              Open the ready-made MCDA filter
            </Link>
          ) : null}
        </aside>

        <div className="finder-results">
          {result ? (
            <section className="card finder-summary-card">
              <div className="finder-summary-head">
                <div>
                  <p className="eyebrow">Evidence summary</p>
                  <h2>{result.config_title || 'No matching local dataset yet'}</h2>
                </div>
                <strong>{result.evidence_count} matches</strong>
              </div>
              <p className="lead">
                {result.config_description ||
                  'This query did not match a supported local sample dataset strongly enough to build a comparison.'}
              </p>
              {result.note ? <p className="muted">{result.note}</p> : null}
            </section>
          ) : (
            <section className="card finder-summary-card">
              <p className="eyebrow">Build status</p>
              <h2>The filter is still building.</h2>
              <p className="lead">
                If web research or AI generation takes longer, this job stays in your pending filters list.
              </p>
            </section>
          )}

          {result?.generated_filters?.length ? (
            <section className="card finder-filters-card">
              <div className="finder-section-head">
                <div>
                  <p className="eyebrow">Generated filters</p>
                  <h2>Dynamic facets extracted from matched listings</h2>
                </div>
              </div>
              <div className="finder-filter-grid">
                {result.generated_filters.map((filter) => (
                  <article key={filter.key} className="finder-filter-card">
                    <div className="finder-filter-head">
                      <strong>{filter.label}</strong>
                      <span>{filter.type}</span>
                    </div>
                    {filter.options.length > 0 ? (
                      <div className="finder-option-list">
                        {filter.options.map((option) => (
                          <span key={`${filter.key}-${option.value}`} className="finder-option-chip">
                            {option.label}
                            {typeof option.count === 'number' ? ` · ${option.count}` : ''}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="muted">
                        Range observed: {filter.min} to {filter.max}
                      </p>
                    )}
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {result?.listings?.length ? (
            <section className="card finder-listings-card">
              <div className="finder-section-head">
                <div>
                  <p className="eyebrow">Ranked matches</p>
                  <h2>Initial ranking is relevance-based until you refine the filter.</h2>
                </div>
              </div>
              <div className="finder-listing-grid">
                {result.listings.map((listing) => (
                  <article key={listing.listing_id} className="finder-listing-card">
                    <div className="finder-listing-head">
                      <strong>{listing.title}</strong>
                      <span className="finder-score">Score {listing.score}</span>
                    </div>
                    {listing.subtitle ? <p className="muted">{listing.subtitle}</p> : null}
                    {listing.image_url ? (
                      <img className="finder-listing-image" src={listing.image_url} alt={listing.title} />
                    ) : null}
                    <div className="finder-metadata">
                      {listing.metadata.map((entry) => (
                        <span key={`${listing.listing_id}-${entry.label}`} className="finder-metadata-chip">
                          {entry.label}: {entry.value}
                        </span>
                      ))}
                    </div>
                    {listing.source_url ? (
                      <a href={listing.source_url} target="_blank" rel="noreferrer" className="ghost-link">
                        Source details
                      </a>
                    ) : null}
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {result?.candidates?.length ? (
            <section className="card finder-candidates-card">
              <div className="finder-section-head">
                <div>
                  <p className="eyebrow">Matching configs</p>
                  <h2>Best local datasets for this query</h2>
                </div>
              </div>
              <div className="finder-candidate-grid">
                {result.candidates.map((candidate) => (
                  <article key={candidate.config_key} className="finder-candidate-card">
                    <strong>{candidate.title}</strong>
                    <p className="muted">{candidate.description}</p>
                    <p className="muted">
                      Evidence-backed matches: {candidate.evidence_count} · Score {candidate.match_score}
                    </p>
                    <Link className="ghost-link" to={`/filters/${candidate.config_key}`}>
                      Open filter
                    </Link>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {recentJobs.length > 0 ? (
            <section className="card finder-history-card">
              <div className="finder-section-head">
                <div>
                  <p className="eyebrow">Recent jobs</p>
                  <h2>Local finder history</h2>
                </div>
              </div>
              <div className="finder-history-list">
                {recentJobs.map((recentJob) => (
                  <button
                    key={recentJob.job_id}
                    type="button"
                    className="finder-history-item"
                    onClick={() => {
                      setQuery(recentJob.query);
                      setJob(recentJob);
                      setSearchParams({ q: recentJob.query }, { replace: true });
                    }}
                  >
                    <strong>{recentJob.query}</strong>
                    <span>
                      {recentJob.status} · {recentJob.profile}
                    </span>
                  </button>
                ))}
              </div>
            </section>
          ) : null}
        </div>
      </div>
    </section>
  );
}
