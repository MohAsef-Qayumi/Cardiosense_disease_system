import { FormEvent, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

export function ContactForm() {
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
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
    <form onSubmit={onSubmit} className="glass-panel form-shell form-row">
      <div className="field">
        <input name="firstName" placeholder="First name" required />
      </div>
      <div className="field">
        <input name="lastName" placeholder="Last name" required />
      </div>
      <div className="field">
        <input name="email" placeholder="Email" type="email" required />
      </div>
      <div className="field">
        <select name="topic" required>
          <option value="">Select topic</option>
          <option>Inference API integration</option>
          <option>Model metrics and thresholding</option>
          <option>General collaboration</option>
        </select>
      </div>
      <div className="field full">
        <textarea name="message" rows={4} placeholder="Share your message..." />
      </div>
      <div className="submit-row">
        <button className="btn-primary-cs" type="submit" disabled={loading}>
          {loading ? (
            <span className="spinner-border spinner-border-sm me-2" />
          ) : (
            <i className="bi bi-send" />
          )}
          {loading ? " Sending..." : " Submit"}
        </button>
      </div>
      {error && <p className="auth-status is-visible bad">{error}</p>}
      {submitted && (
        <p className="success-message is-visible">
          Message received. Thank you for reaching out.
        </p>
      )}
    </form>
  );
}
