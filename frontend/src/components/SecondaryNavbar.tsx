import { useEffect, useRef } from 'react';
import type { SyntheticEvent } from 'react';
import { Link } from 'react-router-dom';
import { categories } from '../data/categories';

export default function SecondaryNavbar() {
  const navRef = useRef<HTMLDivElement>(null);
  const enabledConfigs = new Set(['reverb-acoustic-guitars', 'insulin-devices', 'vehicle-catalog']);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      if (!navRef.current) return;
      if (navRef.current.contains(event.target as Node)) return;
      navRef.current.querySelectorAll('details[open]').forEach((detail) => {
        detail.removeAttribute('open');
      });
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      if (!navRef.current) return;
      navRef.current.querySelectorAll('details[open]').forEach((detail) => {
        detail.removeAttribute('open');
      });
    };

    document.addEventListener('click', handleClick);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('click', handleClick);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const handleToggle = (event: SyntheticEvent<HTMLDetailsElement>) => {
    const toggled = event.target instanceof HTMLDetailsElement
      ? event.target
      : event.currentTarget;

    if (!toggled.open) {
      toggled.querySelectorAll('details[open]').forEach((child) => {
        child.removeAttribute('open');
      });
      return;
    }

    document.querySelectorAll('details[open]').forEach((openDetail) => {
      if (openDetail === toggled) return;
      if (openDetail.contains(toggled)) return;
      if (toggled.contains(openDetail)) return;
      openDetail.querySelectorAll('details[open]').forEach((child) => {
        child.removeAttribute('open');
      });
      openDetail.removeAttribute('open');
    });
  };

  return (
    <div className="secondary-nav" ref={navRef}>
      <div className="secondary-title">Categories</div>
      <div className="category-dropdowns">
        {categories.map((category) => (
          <details key={category.key} className="category-dropdown" onToggle={handleToggle}>
            <summary>{category.label}</summary>
            <div className="dropdown-panel">
              <p>{category.description}</p>
              <div className="dropdown-items">
                {category.filterConfigs.map((config) => {
                  const isAvailable = enabledConfigs.has(config.key);
                  if (!isAvailable) {
                    return (
                      <div key={config.key} className="dropdown-item is-disabled" aria-disabled="true">
                        <strong>{config.label}</strong>
                      </div>
                    );
                  }
                  return (
                    <Link
                      key={config.key}
                      to={`/filters/${config.key}`}
                      className="dropdown-item"
                    >
                      <strong>{config.label}</strong>
                    </Link>
                  );
                })}
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
