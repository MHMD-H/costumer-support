import type { ReactNode } from "react";

import { BrandMark } from "../ui/brand-mark";
import { ContourBackground } from "../ui/contour-background";
import { getOnboardingProgressIndex, ONBOARDING_PROGRESS_STEPS, type OnboardingReferenceId } from "../../lib/onboarding-references";

type OnboardingShellProps = {
  children: ReactNode;
  referenceId: OnboardingReferenceId;
  logOutAction?: ReactNode;
};

function ProgressMark({ complete, current }: { complete: boolean; current: boolean }) {
  if (complete) {
    return (
      <svg aria-hidden="true" className="onboarding-progress__check" fill="none" viewBox="0 0 20 20">
        <path d="m4.5 10.3 3.4 3.3 7.6-7.4" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
      </svg>
    );
  }

  return current ? <span aria-hidden="true" className="onboarding-progress__dot" /> : null;
}

export function OnboardingShell({ children, referenceId, logOutAction }: OnboardingShellProps) {
  const activeIndex = getOnboardingProgressIndex(referenceId);

  return (
    <div className="contour-shell onboarding-shell">
      <ContourBackground />

      <header className="onboarding-shell__header">
        <div className="onboarding-shell__header-inner">
          <BrandMark />
          {logOutAction ? <div className="onboarding-shell__logout">{logOutAction}</div> : null}
        </div>
      </header>

      <main className="onboarding-shell__main">
        <div className="onboarding-shell__content">{children}</div>
      </main>

      <nav aria-label="Onboarding progress" className="onboarding-progress">
        <ol className="onboarding-progress__steps">
          {ONBOARDING_PROGRESS_STEPS.map((step, index) => {
            const complete = index < activeIndex;
            const current = index === activeIndex;

            return (
              <li
                aria-current={current ? "step" : undefined}
                className={`onboarding-progress__step${complete ? " onboarding-progress__step--complete" : ""}${current ? " onboarding-progress__step--current" : ""}`}
                key={step.id}
              >
                <span aria-hidden="true" className="onboarding-progress__marker">
                  <ProgressMark complete={complete} current={current} />
                </span>
                <span className="onboarding-progress__label">{step.label}</span>
                {complete ? <span className="sr-only">Completed</span> : null}
              </li>
            );
          })}
        </ol>
      </nav>
    </div>
  );
}
