import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login } from "../auth";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface FieldErrors {
  email?: string;
  password?: string;
  form?: string;
}

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);

  function validate(): FieldErrors {
    const next: FieldErrors = {};
    if (!email.trim()) next.email = "Email is required.";
    else if (!EMAIL_RE.test(email)) next.email = "Enter a valid email address.";
    if (!password) next.password = "Password is required.";
    return next;
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const next = validate();
    setErrors(next);
    if (Object.keys(next).length > 0) return;

    setSubmitting(true);
    const result = login(email.trim(), password);
    setSubmitting(false);
    if ("error" in result) {
      setErrors({ form: result.error });
      return;
    }
    navigate("/dashboard", { replace: true });
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="sidebar-brand-mark">🌍</span>
          <span className="sidebar-brand-name">EcoSphere</span>
        </div>
        <h1 className="auth-title">Sign in</h1>
        <p className="auth-subtitle">Welcome back. Enter your details to continue.</p>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {errors.form && <div className="auth-error-banner">{errors.form}</div>}

          <label className="field">
            <span className="field-label">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={"field-input" + (errors.email ? " field-input--invalid" : "")}
              placeholder="you@company.com"
              autoComplete="email"
            />
            {errors.email && <span className="field-error">{errors.email}</span>}
          </label>

          <label className="field">
            <span className="field-label">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={"field-input" + (errors.password ? " field-input--invalid" : "")}
              placeholder="••••••••"
              autoComplete="current-password"
            />
            {errors.password && <span className="field-error">{errors.password}</span>}
          </label>

          <button type="submit" className="btn btn-primary auth-submit" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="auth-switch">
          Don't have an account? <Link to="/signup">Create one</Link>
        </p>
        <p className="auth-hint">Demo: admin@ecosphere.io / admin123</p>
      </div>
    </div>
  );
}
