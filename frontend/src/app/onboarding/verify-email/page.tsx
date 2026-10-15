import { OnboardingShell } from "../../../components/onboarding/onboarding-shell";
import { VerifyEmailCode } from "../../../components/onboarding/verify-email-code";
import { VerificationLogout } from "../../../components/onboarding/verification-logout";

export default function VerifyEmailPage() {
  return (
    <OnboardingShell logOutAction={<VerificationLogout />} referenceId="verifyEmailCode">
      <VerifyEmailCode />
    </OnboardingShell>
  );
}
