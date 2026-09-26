"use client";

import { useEffect } from "react";

export function ScrollRevealController() {
  useEffect(() => {
    const targets = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    const showEverything = () => targets.forEach((target) => { target.dataset.revealVisible = "true"; });

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) {
      showEverything();
      return;
    }

    let visibleCount = 0;
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        (entry.target as HTMLElement).dataset.revealVisible = "true";
        observer.unobserve(entry.target);
        visibleCount += 1;
      }
      if (visibleCount === targets.length) observer.disconnect();
    }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });

    targets.forEach((target) => observer.observe(target));
    document.documentElement.dataset.scrollReveal = "on";

    return () => {
      observer.disconnect();
      delete document.documentElement.dataset.scrollReveal;
    };
  }, []);

  return null;
}
