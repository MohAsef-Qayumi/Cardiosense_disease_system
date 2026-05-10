import { Link, useNavigate } from "react-router-dom";
import { FormEvent, useState } from "react";
import { useAuth } from "@/context/auth-context";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export function LoginForm() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<"idle" | "ok" | "bad">("idle");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setMessage("Authenticating...");
    setStatus("idle");
    setLoading(true);

    const form = e.currentTarget;
    const email = (form.elements.namedItem("email") as HTMLInputElement)?.value;
    const password = (form.elements.namedItem("password") as HTMLInputElement)
      ?.value;

    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setMessage(data?.detail || "Invalid email or password.");
        setStatus("bad");
        return;
      }

      login(
        data.user.email,
        data.user.full_name,
        data.user.role,
        data.access_token,
      );
      setMessage("Login successful! Redirecting...");
      setStatus("ok");
      setTimeout(() => navigate("/dashboard"), 800);
    } catch {
      setMessage("Could not reach the server. Please try again.");
      setStatus("bad");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="glass-panel auth-card auth-form">
      <span className="section-kicker">Account Access</span>
      <h1 className="section-title">Log in to your account</h1>
      <p className="section-copy">
        Enter your credentials below to access your prediction dashboard.
      </p>
      <div className="field">
        <label htmlFor="email">Email address</label>
        <input
          id="email"
          name="email"
          placeholder="you@example.com"
          type="email"
          required
        />
      </div>
      <div className="field">
        <label htmlFor="password">Password</label>
        <div className="password-wrapper">
          <input
            id="password"
            name="password"
            placeholder="Enter your password"
            type={showPassword ? "text" : "password"}
            required
            minLength={8}
          />
          <button
            type="button"
            className="password-toggle"
            onClick={() => setShowPassword((v) => !v)}
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            <i className={showPassword ? "bi bi-eye-slash" : "bi bi-eye"} />
          </button>
        </div>
      </div>
      <div className="auth-inline">
        <label className="auth-check" htmlFor="rememberMe">
          <input id="rememberMe" type="checkbox" />
          <span>Remember me on this device</span>
        </label>
        <a href="#">Forgot password?</a>
      </div>
      <button className="btn-primary-cs" type="submit" disabled={loading}>
        {loading ? (
          <span className="spinner-border spinner-border-sm me-2" />
        ) : (
          <i className="bi bi-box-arrow-in-right" />
        )}
        {loading ? " Logging in..." : " Log In"}
      </button>
      {message && (
        <p className={`auth-status is-visible ${status}`}>{message}</p>
      )}
      <p className="auth-footnote">
        No account yet? <Link to="/signup">Create one</Link>
      </p>
    </form>
  );
}

export function SignupForm() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<"idle" | "ok" | "bad">("idle");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setMessage("Creating account...");
    setStatus("idle");
    setLoading(true);

    const form = e.currentTarget;
    const fullName = (form.elements.namedItem("fullName") as HTMLInputElement)
      ?.value;
    const email = (form.elements.namedItem("email") as HTMLInputElement)?.value;
    const password = (form.elements.namedItem("password") as HTMLInputElement)
      ?.value;
    const confirm = (
      form.elements.namedItem("passwordConfirm") as HTMLInputElement
    )?.value;
    const role = (form.elements.namedItem("role") as HTMLSelectElement)?.value;

    if (password !== confirm) {
      setMessage("Passwords do not match.");
      setStatus("bad");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ full_name: fullName, email, password, role }),
      });

      const data = await res.json();

      if (!res.ok) {
        setMessage(
          data?.detail || "Could not create account. Please try again.",
        );
        setStatus("bad");
        return;
      }

      login(
        data.user.email,
        data.user.full_name,
        data.user.role,
        data.access_token,
      );
      setMessage("Account created! Redirecting...");
      setStatus("ok");
      setTimeout(() => navigate("/dashboard"), 800);
    } catch {
      setMessage("Could not reach the server. Please try again.");
      setStatus("bad");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="glass-panel auth-card auth-form">
      <span className="section-kicker">Registration</span>
      <h1 className="section-title">Create your account</h1>
      <p className="section-copy">
        Fill out the form below to set up your CardioSense workspace.
      </p>
      <div className="field">
        <label htmlFor="fullName">Full name</label>
        <input
          id="fullName"
          name="fullName"
          placeholder="Your full name"
          required
        />
      </div>
      <div className="field">
        <label htmlFor="emailSignup">Email address</label>
        <input
          id="emailSignup"
          name="email"
          placeholder="you@example.com"
          type="email"
          required
        />
      </div>
      <div className="field">
        <label htmlFor="roleSignup">Account type</label>
        <select id="roleSignup" name="role" defaultValue="student">
          <option value="student">Student / Researcher</option>
          <option value="patient">Patient</option>
          <option value="clinical">Clinical Team</option>
        </select>
      </div>
      <div className="field">
        <label htmlFor="passwordSignup">Password</label>
        <input
          id="passwordSignup"
          name="password"
          placeholder="Create a strong password (min 8 chars)"
          type="password"
          required
          minLength={8}
        />
        <p className="field-note">
          Use at least 8 characters with a mix of letters and numbers.
        </p>
      </div>
      <div className="field">
        <label htmlFor="passwordConfirmSignup">Confirm password</label>
        <input
          id="passwordConfirmSignup"
          name="passwordConfirm"
          placeholder="Re-enter password"
          type="password"
          required
          minLength={8}
        />
      </div>
      <label className="auth-check" htmlFor="agreeTerms">
        <input id="agreeTerms" type="checkbox" required />
        <span>I agree to the platform terms and educational-use policy.</span>
      </label>
      <button className="btn-primary-cs" type="submit" disabled={loading}>
        {loading ? (
          <span className="spinner-border spinner-border-sm me-2" />
        ) : (
          <i className="bi bi-person-check" />
        )}
        {loading ? " Creating..." : " Create Account"}
      </button>
      {message && (
        <p className={`auth-status is-visible ${status}`}>{message}</p>
      )}
      <p className="auth-footnote">
        Already registered? <Link to="/login">Log in</Link>
      </p>
    </form>
  );
}
