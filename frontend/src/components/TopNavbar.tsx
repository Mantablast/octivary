import { Link } from 'react-router-dom';

export default function TopNavbar() {
  return (
    <header className="top-nav">
      <div className="brand">
        <Link to="/">Octivary</Link>
        <span className="tagline">Rank listings your way.</span>
      </div>
      <nav className="top-actions">
        <Link className="ghost-link" to="/account">Account</Link>
        <Link className="ghost-link" to="/saved/placeholder">Saved searches</Link>
        <button className="cta">Sign in</button>
      </nav>
    </header>
  );
}
