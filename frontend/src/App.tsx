import { Routes, Route, useLocation } from 'react-router-dom';
import TopNavbar from './components/TopNavbar';
import SiteFooter from './components/SiteFooter';
import CategoryList from './pages/CategoryList';
import FilterPage from './pages/FilterPage';
import DynamicFinder from './pages/DynamicFinder';
import Account from './pages/Account';
import SavedSearchDetail from './pages/SavedSearchDetail';
import Privacy from './pages/Privacy';
import Terms from './pages/Terms';

export default function App() {
  const location = useLocation();
  const showMainFooter = location.pathname === '/' || location.pathname === '/finder';

  return (
    <div className="app-shell">
      <TopNavbar />
      <main className="page">
        <Routes>
          <Route path="/" element={<DynamicFinder />} />
          <Route path="/finder" element={<DynamicFinder />} />
          <Route path="/categories" element={<CategoryList />} />
          <Route path="/filters/:configKey" element={<FilterPage />} />
          <Route path="/generated/:jobId" element={<FilterPage />} />
          <Route path="/account" element={<Account />} />
          <Route path="/saved/:id" element={<SavedSearchDetail />} />
          <Route path="/terms" element={<Terms />} />
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
      {showMainFooter ? <SiteFooter /> : null}
    </div>
  );
}
