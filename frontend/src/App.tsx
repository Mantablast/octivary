import { Routes, Route, Link } from 'react-router-dom';
import TopNavbar from './components/TopNavbar';
import SecondaryNavbar from './components/SecondaryNavbar';
import ConsentBanner from './components/ConsentBanner';
import Home from './pages/Home';
import CategoryList from './pages/CategoryList';
import FilterPage from './pages/FilterPage';
import Account from './pages/Account';
import SavedSearchDetail from './pages/SavedSearchDetail';
import Privacy from './pages/Privacy';

export default function App() {
  return (
    <div className="app-shell">
      <TopNavbar />
      <SecondaryNavbar />
      <main className="page">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/categories" element={<CategoryList />} />
          <Route path="/filters/:configKey" element={<FilterPage />} />
          <Route path="/account" element={<Account />} />
          <Route path="/saved/:id" element={<SavedSearchDetail />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route
            path="*"
            element={
              <section className="card">
                <h1>Page not found</h1>
                <p>Try a filter from the menu or head back home.</p>
              </section>
            }
          />
        </Routes>
      </main>
      <footer className="nav-footer">
        <div className="nav-footer-links">
          <Link to="/providers">Provider List</Link>
          <Link to="/about">About Us</Link>
          <Link to="/privacy-settings">Privacy Settings</Link>
          <Link to="/giving">Giving & Outreach</Link>
          <Link to="/accessibility">Accessibility</Link>
          <Link to="/feature-listings">Feature Your Listings</Link>
          <Link to="/host">Host Octivary</Link>
          <Link to="/news">News</Link>
          <Link to="/contact">Contact</Link>
        </div>
        <div className="nav-footer-social">
          <a href="#" aria-label="Octivary on X" className="social-icon">X</a>
          <a href="#" aria-label="Octivary on Instagram" className="social-icon">IG</a>
          <a href="#" aria-label="Octivary on TikTok" className="social-icon">TT</a>
          <a href="#" aria-label="Octivary on YouTube" className="social-icon">YT</a>
        </div>
      </footer>
      <footer className="site-footer">
        <Link to="/terms">Terms of Use</Link>
        <Link to="/privacy">Privacy Policy</Link>
        <span>Copyright 2026 CozyCabinOps</span>
      </footer>
      <ConsentBanner />
    </div>
  );
}
