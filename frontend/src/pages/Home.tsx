import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <section className="home">
      <div className="hero">
        <div>
          <p className="eyebrow">MCDA filters, smarter choices</p>
          <h1>Rank listings by what matters to you.</h1>
          <p className="lead">
            Octivary lets you tune priorities, compare live listings, and save your best searches.
          </p>
          <div className="hero-actions">
            <Link className="cta" to="/categories">Explore filters</Link>
            <Link className="ghost-link" to="/filters/electric-sedans">Try electric sedans</Link>
          </div>
        </div>
        <div className="hero-card">
          <h3>Priority mix preview</h3>
          <div className="priority-bars">
            <div><span>Price</span><div className="bar" style={{ width: '72%' }} /></div>
            <div><span>Quality</span><div className="bar" style={{ width: '58%' }} /></div>
            <div><span>Speed</span><div className="bar" style={{ width: '40%' }} /></div>
          </div>
          <p className="muted">Save this weighting and re-run anytime.</p>
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
