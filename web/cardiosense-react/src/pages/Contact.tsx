import { useState } from "react";
import { Link } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

export default function Contact() {
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const form = e.currentTarget;
    const firstName = (form.elements.namedItem("firstName") as HTMLInputElement)
      ?.value;
    const lastName = (form.elements.namedItem("lastName") as HTMLInputElement)
      ?.value;
    const email = (form.elements.namedItem("email") as HTMLInputElement)?.value;
    const topic = (form.elements.namedItem("topic") as HTMLSelectElement)
      ?.value;
    const message = (form.elements.namedItem("message") as HTMLTextAreaElement)
      ?.value;
    try {
      const res = await fetch(`${API_BASE}/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ firstName, lastName, email, topic, message }),
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data?.detail || "Could not send message. Please try again.");
        return;
      }
      setSubmitted(true);
      form.reset();
    } catch {
      setError("Could not reach the server. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <section className="page-hero">
        <div className="container">
          <div className="breadcrumbs" data-reveal>
            <Link to="/">Overview</Link>
            <span>/</span>
            <span className="current">Contact</span>
          </div>
          <h1 className="section-title" data-reveal>
            Connect with the project team
          </h1>
          <p className="page-subtitle" data-reveal>
            Reach out for implementation walkthroughs, code reviews, testing
            discussions, or collaboration around model operations.
          </p>
        </div>
      </section>

      <section className="section-block">
        <div className="container">
          <div className="row g-4 align-items-start">
            <div className="col-lg-4" data-reveal>
              <div className="contact-grid">
                <article className="contact-card">
                  <h3 className="contact-title">Project support</h3>
                  <p className="contact-copy mt-2">
                    For architecture or implementation questions.
                  </p>
                  <p className="contact-copy mt-2">
                    <strong>Email:</strong> cardiosense.project@university.edu
                  </p>
                </article>

                <article className="contact-card">
                  <h3 className="contact-title">Demo sessions</h3>
                  <p className="contact-copy mt-2">
                    Book a walkthrough of inference routes and model metrics.
                  </p>
                  <p className="contact-copy mt-2">
                    <strong>Window:</strong> Weekdays, 10:00 - 17:00
                  </p>
                </article>

                <article className="contact-card">
                  <h3 className="contact-title">Repository context</h3>
                  <p className="contact-copy mt-2">
                    Please include branch details and endpoint version in your
                    message.
                  </p>
                </article>
              </div>
            </div>

            <div className="col-lg-8" data-reveal>
              <div className="glass-panel form-shell">
                <span className="section-kicker">Send Message</span>
                <h2 className="section-title mt-2">Project feedback form</h2>
                <p className="section-copy mt-2">
                  This form is for project communication only and does not
                  collect medical records.
                </p>

                <form onSubmit={handleSubmit} className="form-row mt-3">
                  <div className="field">
                    <label htmlFor="firstName">First name</label>
                    <input
                      id="firstName"
                      name="firstName"
                      type="text"
                      required
                    />
                  </div>

                  <div className="field">
                    <label htmlFor="lastName">Last name</label>
                    <input id="lastName" name="lastName" type="text" required />
                  </div>

                  <div className="field">
                    <label htmlFor="email">Email</label>
                    <input id="email" name="email" type="email" required />
                  </div>

                  <div className="field">
                    <label htmlFor="topic">Topic</label>
                    <select id="topic" name="topic" required>
                      <option value="" selected disabled>
                        Select topic
                      </option>
                      <option>Inference API integration</option>
                      <option>Model metrics and thresholding</option>
                      <option>Dataset and preprocessing</option>
                      <option>Deployment and operations</option>
                      <option>General collaboration</option>
                    </select>
                  </div>

                  <div className="field full">
                    <label htmlFor="message">Message</label>
                    <textarea
                      id="message"
                      name="message"
                      placeholder="Share your question or feedback..."
                      rows={4}
                    ></textarea>
                  </div>

                  <div className="submit-row">
                    <span className="submit-hint">
                      Expected response time: within one working day.
                    </span>
                    <button
                      className="btn-primary-cs"
                      type="submit"
                      disabled={loading}
                    >
                      {loading ? (
                        <span className="spinner-border spinner-border-sm me-2" />
                      ) : (
                        <i className="bi bi-send"></i>
                      )}
                      {loading ? " Sending..." : " Submit"}
                    </button>
                  </div>
                </form>

                {error && <p className="auth-status is-visible bad">{error}</p>}
                {submitted && (
                  <div className="success-message is-visible">
                    Message received. Thank you for supporting the CardioSense
                    AI project.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section-block alt">
        <div className="container">
          <div className="feature-grid">
            <article className="feature-card" data-reveal>
              <span className="feature-icon">
                <i className="bi bi-journal-text"></i>
              </span>
              <h3 className="feature-title">Before contacting</h3>
              <p className="feature-copy">
                Review README and runbook to include precise context in
                technical questions.
              </p>
            </article>

            <article className="feature-card" data-reveal>
              <span className="feature-icon">
                <i className="bi bi-clipboard2-data"></i>
              </span>
              <h3 className="feature-title">Useful details</h3>
              <p className="feature-copy">
                Attach endpoint path, payload sample, and error details for
                faster troubleshooting.
              </p>
            </article>

            <article className="feature-card" data-reveal>
              <span className="feature-icon">
                <i className="bi bi-shield-check"></i>
              </span>
              <h3 className="feature-title">Data policy</h3>
              <p className="feature-copy">
                Do not share sensitive personal health data through this
                frontend contact form.
              </p>
            </article>
          </div>
        </div>
      </section>
    </>
  );
}
