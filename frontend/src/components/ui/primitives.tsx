import Link from "next/link";
import type { AnchorHTMLAttributes, ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

type PrimaryButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { children: ReactNode };

export function PrimaryButton({ className = "", children, ...props }: PrimaryButtonProps) {
  return <button className={`primary-button ${className}`} {...props}>{children}</button>;
}

type TextLinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode };

export function TextLink({ className = "", href, children, ...props }: TextLinkProps) {
  return <Link className={`text-link ${className}`} href={href} {...props}>{children}</Link>;
}

type SectionContainerProps = HTMLAttributes<HTMLDivElement> & { children: ReactNode };

export function SectionContainer({ className = "", children, ...props }: SectionContainerProps) {
  return <div className={`section-container ${className}`} {...props}>{children}</div>;
}

type ProductPreviewFrameProps = HTMLAttributes<HTMLDivElement> & { children: ReactNode };

export function ProductPreviewFrame({ className = "", children, ...props }: ProductPreviewFrameProps) {
  return <div className={`product-preview-frame ${className}`} {...props}>{children}</div>;
}

export function FieldHelp({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <p className={`field-help ${className}`}>{children}</p>;
}

export function FieldError({ children, id, className = "" }: { children: ReactNode; id?: string; className?: string }) {
  return <p className={`field-error ${className}`} id={id} role="alert">{children}</p>;
}
