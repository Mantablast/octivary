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
      <footer className="footer">
        <span>Octivary</span>
        <span>Config-driven MCDA search</span>
        <Link to="/privacy">Privacy</Link>
      </footer>
      <ConsentBanner />
    </div>
  );
}
