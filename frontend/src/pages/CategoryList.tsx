import { Link } from 'react-router-dom';
import { categories } from '../data/categories';

export default function CategoryList() {
  return (
    <section className="section">
      <h1>All filters</h1>
      <p className="lead">
        Each dropdown item maps to a dedicated filter config. Pick a filter and adjust priorities.
      </p>
      <div className="category-grid">
        {categories.map((category) => (
          <div key={category.key} id={category.key} className="card">
            <h2>{category.label}</h2>
            <p className="muted">{category.description}</p>
            <div className="filter-list">
              {category.filterConfigs.map((config) => (
                <Link
                  key={config.key}
                  to={`/filters/${config.key}`}
                  className="filter-link"
                >
                  <span>{config.label}</span>
                  <span className="muted">{config.description}</span>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
