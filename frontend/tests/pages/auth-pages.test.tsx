import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import LoginPage from "../../src/app/login/page";
import ResetPasswordPage from "../../src/app/reset-password/page";

describe("dashboard authentication pages", () => {
  it("renders the sign-in form and account-flow controls", () => {
    const html = renderToStaticMarkup(<LoginPage />);

    expect(html).toContain("Sign in");
    expect(html).toContain('type="email"');
    expect(html).toContain('type="password"');
    expect(html).toContain('id="email"');
    expect(html).toContain('id="password"');
    expect(html).toContain("required");
    expect(html).toContain('minLength="8"');
    expect(html).toContain("Create an account");
    expect(html).toContain("Forgot your password?");
  });

  it("renders a required new-password form for a recovery link", () => {
    const html = renderToStaticMarkup(<ResetPasswordPage />);

    expect(html).toContain("Reset your password");
    expect(html).toContain('name="password"');
    expect(html).toContain("required");
    expect(html).toContain('minLength="8"');
  });
});
