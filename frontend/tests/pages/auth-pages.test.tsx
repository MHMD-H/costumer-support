import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import LoginPage from "../../src/app/login/page";
import RegisterPage from "../../src/app/register/page";
import ForgotPasswordPage from "../../src/app/forgot-password/page";
import ResetPasswordPage from "../../src/app/reset-password/page";
import AccessDeniedPage from "../../src/app/access-denied/page";

describe("dashboard authentication pages", () => {
  it("renders a dashboard-only login with accessible required fields and account paths", () => {
    const html = renderToStaticMarkup(<LoginPage />);

    expect(html).toContain("Log in");
    expect(html).toContain("Turn your store data into clearer, faster decisions.");
    expect(html).toContain("Your business data stays private to your team.");
    expect(html).toContain("Use the email address associated with your Shopify store.");
    expect(html).toContain('type="email"');
    expect(html).toContain('type="password"');
    expect(html).toContain('id="auth-email"');
    expect(html).toContain('id="auth-password"');
    expect(html).toContain('autoComplete="current-password"');
    expect(html).toContain("required");
    expect(html).toContain('minLength="8"');
    expect(html).toContain("Create an account");
    expect(html).toContain("Forgot password?");
    expect(html).toContain("Shopify shoppers use the storefront chat without logging in.");
  });

  it("renders registration and recovery form states", () => {
    const registerHtml = renderToStaticMarkup(<RegisterPage />);
    const forgotHtml = renderToStaticMarkup(<ForgotPasswordPage />);

    expect(registerHtml).toContain("Create an account");
    expect(registerHtml).toContain('autoComplete="new-password"');
    expect(registerHtml).toContain("Log in");
    expect(forgotHtml).toContain("Forgot password?");
    expect(forgotHtml).toContain("Send reset link");
    expect(forgotHtml).toContain('type="email"');
  });

  it("checks a recovery session before showing password reset and renders permission-denied state", () => {
    const html = renderToStaticMarkup(<ResetPasswordPage />);
    const deniedHtml = renderToStaticMarkup(<AccessDeniedPage />);

    expect(html).toContain("Choose a new password");
    expect(html).toContain("Checking your password reset link");
    expect(html).not.toContain("Update password");
    expect(deniedHtml).toContain("Dashboard access unavailable");
    expect(deniedHtml).toContain("store administrator");
  });
});
