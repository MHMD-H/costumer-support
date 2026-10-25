export const ONBOARDING_REFERENCES = {
  verifyEmailCode: {
    name: "Verify email code",
    referenceSvgPath: "/images/onboarding-reference/verify-email-code.svg",
    route: "/onboarding/verify-email",
    accessibleDescription: "Reference for verifying a dashboard user's email address.",
    progressStep: "verifyEmail",
  },
  connectShopifyStore: {
    name: "Connect your Shopify store",
    referenceSvgPath: "/images/onboarding-reference/connect-shopify-store.svg",
    route: "/onboarding/connect-shopify",
    accessibleDescription: "Reference for securely connecting a merchant's Shopify store.",
    progressStep: "connectStore",
  },
  enterShopifyDomain: {
    name: "Enter your Shopify store address",
    referenceSvgPath: "/images/onboarding-reference/enter-shopify-domain.svg",
    route: "/onboarding/shopify-domain",
    accessibleDescription: "Reference for entering the myshopify.com address assigned to a store.",
    progressStep: "connectStore",
  },
  connectingShopifyStore: {
    name: "Connecting your store securely",
    referenceSvgPath: "/images/onboarding-reference/connecting-shopify-store.svg",
    route: "/onboarding/shopify-connecting",
    accessibleDescription: "Reference for the secure connection progress screen after Shopify authorization.",
    progressStep: "authorizeShopify",
  },
  shopifyStoreReady: {
    name: "Your Shopify store is ready",
    referenceSvgPath: "/images/onboarding-reference/shopify-store-ready.svg",
    route: "/onboarding/shopify-ready",
    accessibleDescription: "Reference for the confirmed connected-store success screen.",
    progressStep: "startExploring",
  },
} as const;

export type OnboardingReferenceId = keyof typeof ONBOARDING_REFERENCES;
export type OnboardingProgressStepId = (typeof ONBOARDING_REFERENCES)[OnboardingReferenceId]["progressStep"];

export const ONBOARDING_PROGRESS_STEPS = [
  { id: "account", label: "Account" },
  { id: "verifyEmail", label: "Verify email" },
  { id: "connectStore", label: "Connect store" },
  { id: "authorizeShopify", label: "Authorize Shopify" },
  { id: "startExploring", label: "Start exploring" },
] as const;

export function getOnboardingProgressIndex(referenceId: OnboardingReferenceId): number {
  const activeStep = ONBOARDING_REFERENCES[referenceId].progressStep;
  return ONBOARDING_PROGRESS_STEPS.findIndex((step) => step.id === activeStep);
}
