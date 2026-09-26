import Link from "next/link";

import { BrandMark } from "../components/ui/brand-mark";
import { ContourBackground } from "../components/ui/contour-background";
import { ProductPreviewImage } from "../components/ui/product-preview";
import { ScrollRevealController } from "../components/ui/scroll-reveal";
import { SectionContainer, TextLink } from "../components/ui/primitives";

function CheckIcon() {
  return (
    <svg aria-hidden="true" className="check-icon" fill="none" viewBox="0 0 20 20">
      <circle cx="10" cy="10" r="9" fill="currentColor" />
      <path d="m6.2 10.2 2.5 2.4 5.1-5.2" stroke="white" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
    </svg>
  );
}

function CheckList({ items, className = "" }: { items: string[]; className?: string }) {
  return (
    <ul className={`check-list ${className}`}>
      {items.map((item) => (
        <li key={item}>
          <CheckIcon />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function HomePage() {
  return (
    <div className="contour-shell landing-page">
      <ContourBackground />
      <ScrollRevealController />
      <header className="landing-header">
        <SectionContainer className="landing-header__inner">
          <BrandMark />
          <TextLink href="/login">Log in</TextLink>
        </SectionContainer>
      </header>

      <main>
        <section aria-labelledby="hero-title" className="landing-hero">
          <SectionContainer className="landing-hero__inner">
            <div aria-hidden="true" className="hero-annotation">
              <span>Your Shopify store,<br />more possible.</span>
              <svg fill="none" viewBox="0 0 100 72">
                <path d="M93 3C90 30 76 47 47 56" stroke="currentColor" strokeLinecap="round" strokeWidth="1.5" />
                <path d="m51 48-7 9 11 1" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" />
              </svg>
            </div>
            <div className="landing-hero__copy" data-reveal>
              <p className="landing-hero__context">Your store data. A brighter tomorrow.</p>
              <h1 className="landing-hero__title" id="hero-title">
                <span>Grow sales and productivity</span>{" "}
                <span>with the data your store already has.</span>
              </h1>
              <p className="landing-hero__description">
                Bring sales, orders, products, and team knowledge into one workspace, so your team can see what’s happening and find clearer answers.
              </p>
              <Link className="primary-button landing-hero__cta" href="/login">
                <span>Get started</span>
                <svg aria-hidden="true" fill="none" viewBox="0 0 20 20">
                  <path d="M3.5 10h12m-5-5 5 5-5 5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
                </svg>
              </Link>
            </div>

            <div className="product-preview-frame landing-hero__preview" data-reveal>
              <ProductPreviewImage id="dashboardOverview" priority sizes="(max-width: 40rem) 100vw, (max-width: 75rem) 92vw, 1152px" />
            </div>
          </SectionContainer>
        </section>

        <section aria-labelledby="dashboard-intelligence-title" className="story-section dashboard-story">
          <SectionContainer className="story-section__inner dashboard-story__inner">
            <div className="story-section__copy" data-reveal>
              <p className="story-section__context">For authenticated store teams</p>
              <h2 className="story-section__title" id="dashboard-intelligence-title">
                Ask the questions behind your numbers.
              </h2>
              <p className="story-section__lead">
                Get clear, accurate answers &amp; decisions using your store data.
              </p>
              <p className="story-section__body">
                Ask about Products, Orders, Sales, and Campaigns from your owner dashboard. The assistant uses read-only store information, so your team stays in control.
              </p>
              <CheckList className="dashboard-story__sources" items={["Products", "Orders", "Sales", "Campaigns"]} />
            </div>
            <div className="product-preview-frame dashboard-story__preview" data-reveal>
              <ProductPreviewImage id="assistantAnswer" sizes="(max-width: 40rem) 100vw, (max-width: 75rem) 50vw, 560px" />
            </div>
          </SectionContainer>
        </section>

        <section aria-labelledby="knowledge-title" className="story-section knowledge-story">
          <SectionContainer className="story-section__inner knowledge-story__inner">
            <div className="product-preview-frame knowledge-story__preview" data-reveal>
              <ProductPreviewImage id="knowledgeLibrary" sizes="(max-width: 40rem) 100vw, (max-width: 75rem) 50vw, 560px" />
            </div>
            <div className="story-section__copy knowledge-story__copy" data-reveal>
              <p className="story-section__context">Knowledge you control</p>
              <h2 className="story-section__title" id="knowledge-title">
                One source of truth for your team.
              </h2>
              <p className="story-section__body">
                Authorized dashboard users can upload and organize useful information, then choose whether each document is Internal or Public.
              </p>
              <div aria-label="Document visibility" className="knowledge-visibility">
                <div className="knowledge-visibility__item">
                  <span aria-hidden="true" className="knowledge-visibility__icon knowledge-visibility__icon--internal">
                    <svg fill="none" viewBox="0 0 20 20"><rect x="4.5" y="8.5" width="11" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.6"/><path d="M7 8.5V6a3 3 0 0 1 6 0v2.5" stroke="currentColor" strokeWidth="1.6"/></svg>
                  </span>
                  <div><h3>Internal</h3><p>Available to authorized store teams.</p></div>
                </div>
                <div className="knowledge-visibility__item">
                  <span aria-hidden="true" className="knowledge-visibility__icon">
                    <svg fill="none" viewBox="0 0 20 20"><circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.6"/><path d="M3.5 10h13M10 3c1.8 1.9 2.5 4.2 2.5 7s-.7 5.1-2.5 7c-1.8-1.9-2.5-4.2-2.5-7S8.2 4.9 10 3Z" stroke="currentColor" strokeWidth="1.4"/></svg>
                  </span>
                  <div><h3>Public</h3><p>May inform customer-facing widget answers.</p></div>
                </div>
              </div>
            </div>
          </SectionContainer>
        </section>

        <section aria-labelledby="widget-title" className="story-section widget-story">
          <SectionContainer className="story-section__inner widget-story__inner">
            <div className="story-section__copy" data-reveal>
              <p className="story-section__context">For your storefront</p>
              <h2 className="story-section__title" id="widget-title">
                Helpful answers for customers. Private data stays private.
              </h2>
              <p className="story-section__body">
                Add a customer-friendly chat widget to your Shopify store. It answers from public product and policy knowledge, so shoppers can get help without creating an account.
              </p>
              <CheckList
                className="widget-story__limits"
                items={[
                  "Public product and policy knowledge only",
                  "Customer-safe answers",
                  "No customer account required",
                ]}
              />
            </div>
            <div className="product-preview-frame widget-story__preview" data-reveal>
              <ProductPreviewImage id="shopifyChatWidget" sizes="(max-width: 40rem) 100vw, (max-width: 75rem) 50vw, 560px" />
            </div>
          </SectionContainer>
        </section>

        <section aria-labelledby="closing-title" className="landing-closing">
          <SectionContainer className="landing-closing__inner" data-reveal>
            <h2 id="closing-title">Bring your store’s knowledge and numbers together.</h2>
            <p>Join store teams making clearer, more confident decisions with AI Commerce Copilot.</p>
            <div className="landing-closing__actions">
              <Link className="primary-button" href="/login">
                <span>Get started</span>
                <svg aria-hidden="true" fill="none" viewBox="0 0 20 20">
                  <path d="M3.5 10h12m-5-5 5 5-5 5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
                </svg>
              </Link>
              <TextLink href="/login">Log in</TextLink>
            </div>
          </SectionContainer>
        </section>
      </main>

      <footer className="landing-footer">
        <SectionContainer className="landing-footer__inner">
          <BrandMark />
          <p>Built for Shopify merchants <span aria-hidden="true">|</span> A smarter way forward</p>
        </SectionContainer>
      </footer>
    </div>
  );
}
