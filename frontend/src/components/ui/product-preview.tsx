"use client";

import Image from "next/image";
import { useState } from "react";

import { PRODUCT_PREVIEWS, type ProductPreviewId } from "../../lib/product-previews";

type ProductPreviewImageProps = {
  id: ProductPreviewId;
  sizes?: string;
  priority?: boolean;
};

export function ProductPreviewImage({
  id,
  sizes = "(max-width: 40rem) 100vw, (max-width: 75rem) 90vw, 72rem",
  priority = false,
}: ProductPreviewImageProps) {
  const preview = PRODUCT_PREVIEWS[id];
  const [unavailable, setUnavailable] = useState(false);

  return (
    <div
      className="product-preview-image"
      data-preview-id={id}
    >
      {unavailable ? (
        <div className="product-preview-fallback" role="img" aria-label={`${preview.alt} Preview unavailable.`}>
          <svg aria-hidden="true" className="product-preview-fallback-mark" fill="none" viewBox="0 0 32 32">
            <rect x="1" y="1" width="30" height="30" rx="9" stroke="currentColor" />
            <path d="M9 21h14M11 17l4-4 3 3 4-5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" />
          </svg>
          <span>Product preview unavailable</span>
        </div>
      ) : (
        <Image
          alt={preview.alt}
          className="product-preview-image__asset"
          fill
          onError={() => setUnavailable(true)}
          priority={priority}
          sizes={sizes}
          src={preview.src}
        />
      )}
    </div>
  );
}
