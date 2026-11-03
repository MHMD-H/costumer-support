import { AuthenticatedOnboardingGuard } from "../../../components/onboarding/authenticated-onboarding-guard";
import { OnboardingShell } from "../../../components/onboarding/onboarding-shell";
import { ShopifyDomainEntry } from "../../../components/onboarding/shopify-domain-entry";
import { VerificationLogout } from "../../../components/onboarding/verification-logout";

export default function ShopifyDomainPage() {
  return (
    <AuthenticatedOnboardingGuard>
      <OnboardingShell logOutAction={<VerificationLogout />} referenceId="enterShopifyDomain">
        <ShopifyDomainEntry />
      </OnboardingShell>
    </AuthenticatedOnboardingGuard>
  );
}
