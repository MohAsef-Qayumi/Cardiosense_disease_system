import { LoginForm } from "@/components/auth-forms";

export default function Login() {
  return (
    <section className="auth-main">
      <div className="container">
        <div className="auth-layout">
          <aside className="auth-aside">
            <span className="section-kicker">Welcome Back</span>
            <h1>Continue monitoring heart disease risk with confidence.</h1>
            <p>Sign in to access your prediction workspace and continue where you left off.</p>
            <ul className="auth-points">
              <li>Secure access to prediction history and confidence outputs</li>
              <li>Fast entry to API-backed and fallback demo modes</li>
              <li>Ready for MongoDB user storage integration</li>
            </ul>
            <div className="auth-aside-metrics">
              <article className="auth-metric"><strong>0.804</strong><span>Test ROC-AUC</span></article>
              <article className="auth-metric"><strong>73.4%</strong><span>Test Accuracy</span></article>
              <article className="auth-metric"><strong>0.53</strong><span>Decision Threshold</span></article>
            </div>
          </aside>
          <LoginForm />
        </div>
      </div>
    </section>
  );
}
