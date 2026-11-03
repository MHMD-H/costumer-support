import Link from "next/link";

import { AssuranceCheckIcon, OnboardingArrowIcon, ShopifyBagIcon } from "./shopify-icons";

const ASSURANCES = [
  "Verify your store ownership",
  "Keep your store data private",
  "Choose what your team can access",
] as const;

export function ConnectShopifyStore() {
  return (
    <section aria-labelledby="connect-shopify-title" className="shopify-connect onboarding-stage">
      <div className="onboarding-stage__intro">
        <p className="onboarding-stage__eyebrow">Set up your workspace</p>
        <h1 id="connect-shopify-title">Connect your Shopify store</h1>
        <p>Link your store securely to bring products, orders,<br className="onboarding-stage__desktop-break" /> sales, and team knowledge into one workspace.</p>
      </div>

      <div className="shopify-connect__card onboarding-stage__card">
        <ShopifyBagIcon />
        <h2>Connect securely with Shopify</h2>
        <ul className="shopify-connect__assurances">
          {ASSURANCES.map((assurance) => (
            <li key={assurance}><AssuranceCheckIcon /><span>{assurance}</span></li>
          ))}
        </ul>
        <Link className="primary-button shopify-connect__action" href="/onboarding/shopify-domain">
          Connect Shopify store <OnboardingArrowIcon />
        </Link>
        <p className="shopify-connect__note">You’ll continue to Shopify to approve the connection.</p>
      </div>
    </section>
  );
}
