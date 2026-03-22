import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { DynamicSearchJob } from '../types';

function buildHeaders(): Record<string, string> {
  const headers: Record<string, string> = { accept: 'application/json' };
  const apiToken = (import.meta.env.VITE_API_TOKEN || '').trim();
  if (apiToken) {
    headers.Authorization = `Bearer ${apiToken}`;
  }
  return headers;
}

async function cancelJob(jobId: string): Promise<DynamicSearchJob> {
  const apiBase = (import.meta.env.VITE_API_BASE || '').trim();
  const response = await fetch(`${apiBase}/api/dynamic-search/jobs/${jobId}/cancel`, {
    method: 'POST',
    headers: buildHeaders()
  });
  if (!response.ok) {
    throw new Error('Failed to stop the filter build.');
  }
  return response.json() as Promise<DynamicSearchJob>;
}

export default function Account() {
  const [jobs, setJobs] = useState<DynamicSearchJob[]>([]);
  const [error, setError] = useState('');

  const loadJobs = () => {
    const apiBase = (import.meta.env.VITE_API_BASE || '').trim();
    if (!apiBase) {
      setError('Set VITE_API_BASE to load pending and previous filters.');
      return;
    }
    fetch(`${apiBase}/api/dynamic-search/jobs?limit=20`, { headers: buildHeaders() })
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to load your filter jobs.');
        }
        return response.json() as Promise<DynamicSearchJob[]>;
      })
      .then((data) => {
        setJobs(data);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load your filter jobs.');
      });
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const handleCancel = async (jobId: string) => {
    setError('');
    try {
      const cancelledJob = await cancelJob(jobId);
      setJobs((current) => current.map((job) => (job.job_id === jobId ? cancelledJob : job)));
      loadJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop your filter build.');
    }
  };

  const pendingJobs = jobs.filter(
    (job) => job.status === 'queued' || job.status === 'running' || job.result?.enrichment_status === 'running'
  );
  const previousJobs = jobs.filter(
    (job) => job.status === 'completed' && job.result?.enrichment_status !== 'running'
  );

  return (
    <section className="section">
      <h1>Account</h1>
      <p className="lead">
        Sign up to save filters, review pending builds, and reopen previous MCDA work.
      </p>
      <div className="grid">
        <div className="card">
          <h2>Sign up</h2>
          <label className="field">
            <span>Email</span>
            <input type="email" placeholder="you@example.com" />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" placeholder="••••••••" />
          </label>
          <button className="cta">Continue</button>
        </div>
        <div className="card" id="pending">
          <h2>Pending filters</h2>
          {pendingJobs.length === 0 ? (
            <p className="muted">No filters are building right now.</p>
          ) : (
            <div className="placeholder-list">
              {pendingJobs.map((job) => (
                <div key={job.job_id}>
                  <strong>{job.query}</strong>
                  <div className="muted">
                    {job.result?.enrichment_status === 'running' ? 'enriching' : job.status} ·{' '}
                    {job.result?.enrichment_message || job.current_step}
                  </div>
                  <button
                    type="button"
                    className="mcda-button mcda-button--ghost finder-stop-button"
                    onClick={() => handleCancel(job.job_id)}
                  >
                    Stop search
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="card" id="previous">
          <h2>Previous filters</h2>
          {error ? <p className="muted">{error}</p> : null}
          {previousJobs.length === 0 ? (
            <p className="muted">No completed MCDA filters yet.</p>
          ) : (
            <div className="placeholder-list">
              {previousJobs.map((job) => {
                const href = job.result?.generated_config
                  ? `/generated/${encodeURIComponent(job.job_id)}`
                  : job.result?.config_key
                  ? `/filters/${encodeURIComponent(job.result.config_key)}?dynamicJob=${encodeURIComponent(job.job_id)}`
                  : `/finder?q=${encodeURIComponent(job.query)}`;
                return (
                  <Link key={job.job_id} to={href}>
                    {job.query}
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
