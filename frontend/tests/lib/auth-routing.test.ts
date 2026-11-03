import { describe, expect, it } from "vitest";

import { destinationForConnectionStatus } from "../../src/lib/auth-routing";

describe("post-authentication routing", () => {
  it("routes only from trusted backend connection state", () => {
    expect(destinationForConnectionStatus("connected")).toBe("/dashboard");
    expect(destinationForConnectionStatus("pending")).toBe("/onboarding/connect-shopify");
  });

  it("fails closed for missing, forbidden, or unavailable trusted state", () => {
    expect(destinationForConnectionStatus("signed-out")).toBe("/login?session=expired");
    expect(destinationForConnectionStatus("forbidden")).toBe("/access-denied");
    expect(destinationForConnectionStatus("unavailable")).toBeNull();
  });
});
