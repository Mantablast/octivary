import { Link } from 'react-router-dom';
import { categories } from '../data/categories';

export default function SecondaryNavbar() {
  return (
    <div className="secondary-nav">
      <div className="secondary-title">Categories</div>
      <div className="category-dropdowns">
        {categories.map((category) => (
          <details key={category.key} className="category-dropdown">
            <summary>{category.label}</summary>
            <div className="dropdown-panel">
              <p>{category.description}</p>
              <div className="dropdown-items">
                {category.filterConfigs.map((config) => (
                  <Link
                    key={config.key}
                    to={`/filters/${config.key}`}
                    className="dropdown-item"
                  >
                    <strong>{config.label}</strong>
                    <span className="muted">{config.description}</span>
                  </Link>
                ))}
              </div>
              <Link to={`/categories#${category.key}`} className="dropdown-link">
                View all filters
              </Link>
            </div>
          </details>
        ))}
      </div>
      <Link className="secondary-link" to="/categories">
        All filters
      </Link>
    </div>
  );
}
