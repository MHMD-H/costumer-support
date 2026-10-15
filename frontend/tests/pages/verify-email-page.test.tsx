import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import VerifyEmailPage from "../../src/app/onboarding/verify-email/page";

describe("verify email onboarding page", () => {
  it("renders six labeled code fields, resend, progress, and a logout action", () => {
    const html = renderToStaticMarkup(<VerifyEmailPage />);

    expect(html).toContain("Check your inbox");
    expect(html).toContain("Enter verification code");
    expect(html.match(/inputMode="numeric"/g)).toHaveLength(6);
    expect(html).toContain("Digit 1 of 6");
    expect(html).toContain("Digit 6 of 6");
    expect(html).toContain("Resend code");
    expect(html).toContain("Log out");
    expect(html).toContain("Completed");
    expect(html).toContain('aria-current="step"');
  });
});
