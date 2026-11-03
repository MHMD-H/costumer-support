import { ConnectShopifyStore } from "../../../components/onboarding/connect-shopify-store";
import { AuthenticatedOnboardingGuard } from "../../../components/onboarding/authenticated-onboarding-guard";
import { OnboardingShell } from "../../../components/onboarding/onboarding-shell";
import { VerificationLogout } from "../../../components/onboarding/verification-logout";

export default function ConnectShopifyPage() {
  return (
    <AuthenticatedOnboardingGuard>
      <OnboardingShell logOutAction={<VerificationLogout />} referenceId="connectShopifyStore">
        <ConnectShopifyStore />
      </OnboardingShell>
    </AuthenticatedOnboardingGuard>
  );
}
