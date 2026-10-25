import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { OnboardingShell } from "../../src/components/onboarding/onboarding-shell";
import { ONBOARDING_REFERENCES } from "../../src/lib/onboarding-references";

describe("onboarding shared shell", () => {
  it("renders the five-step progress shell and marks the active reference step", () => {
    const html = renderToStaticMarkup(
      <OnboardingShell referenceId="enterShopifyDomain">
        <section><h1>Onboarding shell preview</h1></section>
      </OnboardingShell>,
    );

    expect(html).toContain("AI Commerce Copilot");
    expect(html).toContain('aria-label="Onboarding progress"');
    expect(html).toContain('aria-current="step"');
    expect(html.match(/<li/g)).toHaveLength(5);
    expect(html).toContain("Account");
    expect(html).toContain("Verify email");
    expect(html).toContain("Connect store");
    expect(html).toContain("Authorize Shopify");
    expect(html).toContain("Start exploring");
    expect(html).toContain("Onboarding shell preview");
    expect(html).not.toContain("Log out");
  });

  it("exposes named visual references and supports an optional logout action", () => {
    expect(Object.keys(ONBOARDING_REFERENCES)).toHaveLength(5);
    for (const reference of Object.values(ONBOARDING_REFERENCES)) {
      const svgPath = resolve(process.cwd(), "public", reference.referenceSvgPath.slice(1));
      expect(reference.accessibleDescription.length).toBeGreaterThan(0);
      expect(reference.route.startsWith("/onboarding/")).toBe(true);
      expect(existsSync(svgPath)).toBe(true);
      expect(existsSync(svgPath.replace(/\.svg$/, ".png"))).toBe(true);
    }
    expect(ONBOARDING_REFERENCES.verifyEmailCode).toMatchObject({
      name: "Verify email code",
      referenceSvgPath: "/images/onboarding-reference/verify-email-code.svg",
      route: "/onboarding/verify-email",
    });

    const html = renderToStaticMarkup(
      <OnboardingShell logOutAction={<button aria-label="Log out of AI Commerce Copilot" type="button">Log out</button>} referenceId="verifyEmailCode">
        <div />
      </OnboardingShell>,
    );
    expect(html).toContain('aria-label="Log out of AI Commerce Copilot"');
    expect(html).toContain(">Log out</button>");
  });
});
