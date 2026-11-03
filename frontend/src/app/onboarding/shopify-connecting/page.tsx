import { ConnectingShopifyStore } from "../../../components/onboarding/connecting-shopify-store";
import { OnboardingShell } from "../../../components/onboarding/onboarding-shell";
import { VerificationLogout } from "../../../components/onboarding/verification-logout";

export default function ShopifyConnectingPage() {
  return (
    <OnboardingShell logOutAction={<VerificationLogout />} referenceId="connectingShopifyStore">
      <ConnectingShopifyStore />
    </OnboardingShell>
  );
}
