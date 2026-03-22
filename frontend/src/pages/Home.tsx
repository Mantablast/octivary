import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function Home() {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) {
      navigate('/finder');
      return;
    }
    navigate(`/finder?q=${encodeURIComponent(trimmed)}`);
  };

  return (
    <section className="home">
      <div className="hero">
        <div>
          <p className="eyebrow">MCDA filters, smarter choices</p>
          <h1>Type a product. Build a comparison from evidence.</h1>
          <p className="lead">
            Octivary now supports a local-first finder flow that turns a raw search term into a
            comparison job with generated filters and ranked matches.
          </p>
          <form className="home-search" onSubmit={handleSubmit}>
            <input
              className="finder-input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Dexcom G7, KJV study bible, Toyota Camry"
            />
            <div className="hero-actions">
              <button className="cta" type="submit">Open finder</button>
              <Link className="ghost-link" to="/categories">Browse existing filters</Link>
            </div>
          </form>
        </div>
        <div className="hero-card">
          <h3>Progressive search preview</h3>
          <div className="priority-bars">
            <div><span>Search job created</span><div className="bar" style={{ width: '96%' }} /></div>
            <div><span>Local evidence loaded</span><div className="bar" style={{ width: '78%' }} /></div>
            <div><span>Dynamic filters generated</span><div className="bar" style={{ width: '62%' }} /></div>
          </div>
          <p className="muted">The local queue flow mirrors the planned cloud polling model.</p>
        </div>
      </div>

      <div className="section weekly-feature">
        <div className="section-header">
          <div>
            <p className="eyebrow">Weekly feature</p>
            <h2>Reverb Acoustic Guitars</h2>
            <p className="lead">
              A rotating spotlight on a single filter preset. We will swap this weekly as new
              provider integrations launch.
            </p>
          </div>
          <Link className="ghost-link" to="/filters/reverb-acoustic-guitars">
            Open full filter
          </Link>
        </div>

        <div className="weekly-grid">
          <aside className="card weekly-sidebar">
            <h3>Filter snapshot</h3>
            <div className="filter-snapshot">
              <div>
                <span>Marketplace</span>
                <strong>Reverb</strong>
              </div>
              <div>
                <span>Price</span>
                <strong>$400 - $1,500</strong>
              </div>
              <div>
                <span>Body style</span>
                <strong>Dreadnought</strong>
              </div>
              <div>
                <span>Condition</span>
                <strong>Used</strong>
              </div>
            </div>
            <div className="priority-mini">
              <span>Priority mix</span>
              <div className="mini-bars">
                <div className="mini-bar" style={{ width: '78%' }} />
                <div className="mini-bar" style={{ width: '55%' }} />
                <div className="mini-bar" style={{ width: '42%' }} />
              </div>
            </div>
          </aside>

          <div className="card weekly-listings">
            <h3>Listings (Top picks)</h3>
            <div className="listing-grid">
              <div className="listing-row">
                <div className="listing-meta">
                  <strong>Martin D-15M</strong>
                  <span className="muted">Score 91 · Warm tone</span>
                </div>
                <span className="price">$1,199</span>
              </div>
              <div className="listing-row">
                <div className="listing-meta">
                  <strong>Taylor 214ce</strong>
                  <span className="muted">Score 88 · Balanced</span>
                </div>
                <span className="price">$999</span>
              </div>
              <div className="listing-row">
                <div className="listing-meta">
                  <strong>Gibson J-45</strong>
                  <span className="muted">Score 84 · Iconic</span>
                </div>
                <span className="price">$1,450</span>
              </div>
            </div>
          </div>

          <aside className="card weekly-insights">
            <h3>Your insights</h3>
            <div className="insight-list">
              <div className="insight-row">
                <strong>12</strong>
                <span>Saved searches</span>
              </div>
              <div className="insight-row">
                <strong>5</strong>
                <span>High priority picks</span>
              </div>
              <div className="insight-row">
                <strong>3</strong>
                <span>Search tools used</span>
              </div>
            </div>
            <div className="insight-cta">
              <p className="muted">Sign up to save weekly insights and get alerts.</p>
              <Link className="cta" to="/account">Sign up</Link>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
