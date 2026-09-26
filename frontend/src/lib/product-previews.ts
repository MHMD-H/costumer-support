export type ProductPreviewId =
  | "dashboardOverview"
  | "assistantAnswer"
  | "knowledgeLibrary"
  | "shopifyChatWidget";

export type ProductPreview = {
  src: string;
  alt: string;
  aspectRatio: { width: number; height: number };
  sectionOwner: "hero" | "dashboard-intelligence" | "knowledge-visibility" | "shopify-widget";
};

export const PRODUCT_PREVIEWS = {
  dashboardOverview: {
    src: "/images/product/dashboard-overview.svg",
    alt: "Owner dashboard overview with sales, orders, product totals, a sales chart, and recent store activity.",
    aspectRatio: { width: 8, height: 5 },
    sectionOwner: "hero",
  },
  assistantAnswer: {
    src: "/images/product/assistant-answer.svg",
    alt: "Internal assistant answer comparing monthly sales, with read-only sales, orders, products, and campaigns sources.",
    aspectRatio: { width: 3, height: 2 },
    sectionOwner: "dashboard-intelligence",
  },
  knowledgeLibrary: {
    src: "/images/product/knowledge-library.svg",
    alt: "Team knowledge library listing documents with clearly labeled Internal or Public visibility and explanations of each audience.",
    aspectRatio: { width: 3, height: 2 },
    sectionOwner: "knowledge-visibility",
  },
  shopifyChatWidget: {
    src: "/images/product/shopify-chat-widget.svg",
    alt: "Shopify storefront product page with a customer chat widget answering a public product care question without requiring an account.",
    aspectRatio: { width: 3, height: 2 },
    sectionOwner: "shopify-widget",
  },
} as const satisfies Record<ProductPreviewId, ProductPreview>;
