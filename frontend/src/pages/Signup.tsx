import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signup } from "../auth";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const ROLES = ["EMPLOYEE", "MANAGER", "ADMIN"];

interface FieldErrors {
  full_name?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
  role?: string;
  form?: string;
}

export default function Signup() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState("EMPLOYEE");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);

  function validate(): FieldErrors {
    const next: FieldErrors = {};
    if (!fullName.trim()) next.full_name = "Full name is required.";
    if (!email.trim()) next.email = "Email is required.";
    else if (!EMAIL_RE.test(email)) next.email = "Enter a valid email address.";
    if (!password) next.password = "Password is required.";
    else if (password.length < 8) next.password = "Password must be at least 8 characters.";
    if (!confirmPassword) next.confirmPassword = "Confirm your password.";
    else if (confirmPassword !== password) next.confirmPassword = "Passwords do not match.";
    if (!role) next.role = "Select a role.";
    return next;
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const next = validate();
    setErrors(next);
    if (Object.keys(next).length > 0) return;

    setSubmitting(true);
    const result = signup({ full_name: fullName.trim(), email: email.trim(), password, role });
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
        <h1 className="auth-title">Create your account</h1>
        <p className="auth-subtitle">Join your organization's ESG workspace.</p>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {errors.form && <div className="auth-error-banner">{errors.form}</div>}

          <label className="field">
            <span className="field-label">Full name</span>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className={"field-input" + (errors.full_name ? " field-input--invalid" : "")}
              placeholder="Ada Admin"
              autoComplete="name"
            />
            {errors.full_name && <span className="field-error">{errors.full_name}</span>}
          </label>

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
            <span className="field-label">Role</span>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className={"field-input" + (errors.role ? " field-input--invalid" : "")}
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            {errors.role && <span className="field-error">{errors.role}</span>}
          </label>

          <label className="field">
            <span className="field-label">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={"field-input" + (errors.password ? " field-input--invalid" : "")}
              placeholder="At least 8 characters"
              autoComplete="new-password"
            />
            {errors.password && <span className="field-error">{errors.password}</span>}
          </label>

          <label className="field">
            <span className="field-label">Confirm password</span>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={"field-input" + (errors.confirmPassword ? " field-input--invalid" : "")}
              placeholder="Re-enter password"
              autoComplete="new-password"
            />
            {errors.confirmPassword && <span className="field-error">{errors.confirmPassword}</span>}
          </label>

          <button type="submit" className="btn btn-primary auth-submit" disabled={submitting}>
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
