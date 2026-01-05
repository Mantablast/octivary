import { useEffect, useRef, useState } from 'react';
import type { SyntheticEvent } from 'react';
import { Link } from 'react-router-dom';

export default function TopNavbar() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const navRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const storedTheme = localStorage.getItem('octivary-theme');
    if (storedTheme === 'dark' || storedTheme === 'light') {
      setTheme(storedTheme);
    }
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    localStorage.setItem('octivary-theme', theme);
  }, [theme]);

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

  useEffect(() => {
    const closeDropdowns = () => {
      if (!navRef.current) return;
      navRef.current.querySelectorAll('details[open]').forEach((detail) => {
        detail.removeAttribute('open');
      });
    };

    const handleClick = (event: MouseEvent) => {
      if (!navRef.current) return;
      if (navRef.current.contains(event.target as Node)) return;
      closeDropdowns();
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      closeDropdowns();
    };

    document.addEventListener('click', handleClick);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('click', handleClick);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  return (
    <header className="top-nav" ref={navRef}>
      <div className="top-nav-spacer" aria-hidden="true" />
      <div className="brand">
        <img src="/assets/logo1.png" alt="Octivary logo" className="brand-logo" />
        <Link to="/">Octivary</Link>
      </div>
      <nav className="top-actions">
        <details className="nav-dropdown" onToggle={handleToggle}>
          <summary>Account</summary>
          <div className="dropdown-panel account-panel">
            <Link to="/saved/placeholder" className="dropdown-item">
              <strong>Saved searches</strong>
            </Link>
            <Link to="/saved/items" className="dropdown-item">
              <strong>Saved items</strong>
            </Link>
            <details className="nav-subdropdown" onToggle={handleToggle}>
              <summary className="dropdown-item">
                <strong>Page theme</strong>
              </summary>
              <div className="subdropdown-panel">
                <button
                  type="button"
                  className="dropdown-item theme-option"
                  onClick={() => setTheme('light')}
                  aria-pressed={theme === 'light'}
                >
                  <strong>Light mode</strong>
                </button>
                <button
                  type="button"
                  className="dropdown-item theme-option"
                  onClick={() => setTheme('dark')}
                  aria-pressed={theme === 'dark'}
                >
                  <strong>Dark mode</strong>
                </button>
              </div>
            </details>
            <Link to="/settings" className="dropdown-item">
              <strong>Settings</strong>
            </Link>
            <button type="button" className="dropdown-item">
              <strong>Log out</strong>
            </button>
          </div>
        </details>
        <button className="cta">Sign in</button>
      </nav>
    </header>
  );
}
