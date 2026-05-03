import { SignupForm } from "@/components/auth-forms";

export default function Signup() {
  return (
    <section className="auth-main">
      <div className="container">
        <div className="auth-layout">
          <aside className="auth-aside">
            <span className="section-kicker">Create Account</span>
            <h1>Set up your CardioSense workspace.</h1>
            <p>Register once to unlock a consistent experience for risk checks and API health tracking.</p>
            <ul className="auth-points">
              <li>Designed for patient, student, and clinical-project use</li>
              <li>Built to connect with your MongoDB auth collection later</li>
              <li>Consistent UI flow across landing, login, and signup</li>
            </ul>
            <div className="auth-aside-metrics">
              <article className="auth-metric"><strong>3 Steps</strong><span>Register, log in, predict</span></article>
              <article className="auth-metric"><strong>FastAPI</strong><span>API ready integration</span></article>
              <article className="auth-metric"><strong>MongoDB</strong><span>Planned persistence layer</span></article>
            </div>
          </aside>
          <SignupForm />
        </div>
      </div>
    </section>
  );
}
