import Link from "next/link";

type BrandMarkProps = { href?: string; className?: string };

export function BrandMark({ href = "/", className = "" }: BrandMarkProps) {
  return (
    <Link aria-label="AI Commerce Copilot home" className={`brand-mark ${className}`} href={href}>
      <svg aria-hidden="true" fill="none" height="32" viewBox="0 0 32 32" width="32">
        <path d="M4.8 27 14.6 6.2c.6-1.3 2.3-1.3 2.9 0L27.2 27h-6.1L16 15.4 11 27H4.8Z" fill="var(--color-brand)" />
        <path d="M12.1 21.2h7.8" stroke="white" strokeLinecap="round" strokeWidth="2.2" />
      </svg>
      <span>AI Commerce Copilot</span>
    </Link>
  );
}
