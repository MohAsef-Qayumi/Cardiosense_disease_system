import { Link } from "react-router-dom";
import { useAuth } from "@/context/auth-context";

export function SiteFooter() {
  const year = new Date().getFullYear();
  const { user } = useAuth();

  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-grid">
          <div>
            <Link to="/" className="brand">
              <span className="brand-mark"><i className="bi bi-heart-pulse-fill" /></span>
              CardioSense <span className="brand-accent">AI</span>
            </Link>
            <p className="footer-copy">
              Heart disease prediction workflow with reproducible training, FastAPI inference, and model lifecycle controls.
            </p>
          </div>
          <div>
            <p className="footer-title">Navigation</p>
            <ul className="footer-links">
              {user ? (
                <>
                  <li><Link to="/dashboard">Dashboard</Link></li>
                  <li><Link to="/about">About</Link></li>
                </>
              ) : (
                <>
                  <li><Link to="/">Home</Link></li>
                  <li><Link to="/about">About</Link></li>
                </>
              )}
            </ul>
          </div>
          <div>
            <p className="footer-title">Auth</p>
            <ul className="footer-links">
              {user ? (
                <li><Link to="/dashboard">My Dashboard</Link></li>
              ) : (
                <>
                  <li><Link to="/login">Log In</Link></li>
                  <li><Link to="/signup">Sign Up</Link></li>
                </>
              )}
              <li><Link to="/contact">Contact</Link></li>
            </ul>
          </div>
          <div>
            <p className="footer-title">Project</p>
            <ul className="footer-links">
              <li><a href="http://127.0.0.1:8000/docs">API Docs</a></li>
              <li><Link to="/">Home</Link></li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <span>Copyright {year} CardioSense AI</span>
          <span>Built for Heart Disease Prediction</span>
        </div>
      </div>
    </footer>
  );
}
