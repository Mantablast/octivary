import { Link } from 'react-router-dom';
import { categories } from '../data/categories';

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

      <div className="section">
        <h2>Popular filters</h2>
        <div className="tile-grid">
          {categories.map((category) => (
            <div key={category.key} className="tile">
              <h3>{category.label}</h3>
              <p>{category.description}</p>
              <div className="tile-links">
                {category.filterConfigs.map((config) => (
                  <Link key={config.key} to={`/filters/${config.key}`} className="tile-link">
                    {config.label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
