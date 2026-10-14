"use client";

import { motion, useInView } from "framer-motion";
import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";

const revealEase = [0.22, 1, 0.36, 1] as const;

type RevealProps = {
  children: ReactNode;
  className?: string;
  delay?: number;
};

function useRevealState(amount: number) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { amount, initial: false, once: false });
  const [hasMeasured, setHasMeasured] = useState(false);
  const [startsInView, setStartsInView] = useState(true);

  useEffect(() => {
    const bounds = ref.current?.getBoundingClientRect();
    setStartsInView(Boolean(bounds && bounds.top < window.innerHeight && bounds.bottom > 0));
    setHasMeasured(true);
  }, []);

  return { ref, isInView: !hasMeasured || startsInView || isInView };
}

export function CopyReveal({ children, className, delay = 0 }: RevealProps) {
  const { ref, isInView } = useRevealState(0.22);

  return (
    <motion.div
      className={`story-reveal ${className ?? ""}`}
      ref={ref}
      initial={false}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 28 }}
      transition={{ duration: 0.55, delay, ease: revealEase }}
    >
      {children}
    </motion.div>
  );
}

export function PreviewReveal({ children, className, direction = "right", delay = 0.13 }: RevealProps & { direction?: "left" | "right" }) {
  const { ref, isInView } = useRevealState(0.2);
  const initialX = direction === "left" ? -36 : 36;

  return (
    <motion.div
      className={`story-reveal ${className ?? ""}`}
      ref={ref}
      initial={false}
      animate={isInView ? { opacity: 1, x: 0, scale: 1 } : { opacity: 0, x: initialX, scale: 0.985 }}
      transition={{ duration: 0.65, delay, ease: revealEase }}
    >
      {children}
    </motion.div>
  );
}
