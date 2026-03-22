import { Link } from 'react-router-dom';

export default function SiteFooter() {
  return (
    <footer className="siteFooter">
      <div className="footer-links">
        <Link to="/privacy">Privacy Policy</Link>
        <Link to="/terms">Terms of Use</Link>
        <a href="https://cozycabinops.com" target="_blank" rel="noreferrer">
          CozyCabinOps
        </a>
      </div>
      <div className="footer-copyright">Copyright {new Date().getFullYear()} Octivary</div>
      <a
        className="footer-donate"
        href="https://ko-fi.com/aimeej"
        target="_blank"
        rel="noreferrer"
        aria-label="Support Octivary on Ko-fi"
      >
        <span className="footer-donate__icon" aria-hidden="true">
          <img src="/kofi.png" alt="Ko-fi" loading="lazy" />
        </span>
      </a>
    </footer>
  );
}
