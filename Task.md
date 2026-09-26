# Security Phase

## Scope

This phase establishes real dashboard authentication, verified merchant-to-
Shopify-store connection, user-to-tenant identity resolution, tenant-scoped
resource access, and role-based authorization.

This phase does not redesign the architecture, add multi-tenant memberships,
implement Row Level Security (RLS), or build an advanced permissions engine
beyond the existing roles and permissions data model.

## Working Rules

- Complete one task at a time.
- Run focused tests after each task.
- Complete a security review after each task before moving to the next one.
- Do not change unrelated code, APIs, schema, or architecture.
- Make the smallest safe change that satisfies the task.
- Use the installed `supabase:supabase` skill for every Supabase Auth, JWT, or
  database decision.
- Use the installed `fastapi` skill for FastAPI dependencies and protected
  routes.
- Use the installed `supabase-postgres-best-practices` skill before proposing
  or changing database schema, foreign keys, or RLS.
- Use `codex-security:security-diff-scan` as the final security review of each
  implemented task that changes project files.

## Task 1: Configure Supabase Authentication

**Goal:** Make Supabase Auth the only owner of signup, login, password reset,
sessions, access tokens, and refresh tokens.

**Required skills:** `supabase:supabase`, `codex-security:security-diff-scan`.

**Expected result:** Dashboard users authenticate through Supabase Auth. The
backend does not store, hash, or validate user passwords itself.

**Tests:** Authentication-flow tests and failure cases for invalid credentials,
missing fields, expired reset links, and invalid reset tokens.

**Security review:** Confirm no service-role key or secret is exposed to the
frontend, and no password is stored in the application database.

## Task 2: Verify Supabase JWTs in FastAPI

**Goal:** Replace placeholder bearer-token acceptance with cryptographic JWT
verification in FastAPI.

**Required skills:** `supabase:supabase`, `fastapi`,
`codex-security:security-diff-scan`.

**Approved implementation direction:** Use `OAuth2PasswordBearer` from
`fastapi.security` only to extract the bearer token from the `Authorization`
header. Use `PyJWT` with cryptographic support to verify the Supabase access
token. `OAuth2PasswordBearer` does not decode or verify JWTs by itself.

**Expected result:** Protected routes accept only valid, unexpired Supabase
access tokens. Verification validates signature, issuer, audience, and expiry.
The verified JWT `sub` is the authenticated Supabase user ID.

**Tests:** Valid token, missing token, malformed token, expired token, wrong
issuer/audience, and invalid signature.

**Security review:** Confirm no request can become authenticated merely because
it has a non-empty `Authorization: Bearer` header.

## Task 3: Link Supabase Auth Users to Application Users

**Goal:** Link `public.users.auth_user_id` to `auth.users.id` with a database
foreign key and use that relation as the application identity bridge.

**Required skills:** `supabase:supabase`, `supabase-postgres-best-practices`,
`codex-security:security-diff-scan`.

**Expected result:** The backend resolves an application user by matching
verified JWT `sub` to `public.users.auth_user_id`.

**Tests:** Matching user is resolved; absent, disabled, or mismatched users are
rejected without falling back to a mock user.

**Security review:** Do not use user-controlled JWT metadata as the source of
tenant or role authorization. The database application-user record is the
source of truth.

## Task 4: Connect a Merchant Shopify Store

**Goal:** Let an authenticated dashboard merchant prove they are authorized to
connect a Shopify store, then link that verified store to the application
backend and tenant record.

**Required skills:** `supabase:supabase`, `fastapi`,
`supabase-postgres-best-practices`, `codex-security:security-diff-scan`.

**Expected result:** An authenticated, linked application user without an
active Shopify connection is sent to a merchant-only Shopify OAuth connection
flow. The backend completes the callback, verifies the Shopify callback
signature and one-time OAuth `state`, exchanges the authorization code on the
server, and uses the canonical Shopify shop identity to create or resolve the
tenant and link it to the application user. A merchant with an active linked
store can enter the dashboard; an unlinked merchant can access only the store
connection onboarding flow.

**Backend and database rules:**

- Start the OAuth flow only for the authenticated application user; bind a
  short-lived, single-use `state` value to that user on the server.
- Verify Shopify HMAC and `state` before exchanging the code. Never trust a
  shop domain, tenant ID, callback URL, or connection status supplied by the
  frontend.
- Store the verified canonical shop domain and connection status with the
  tenant. Link the application user to that tenant only after a successful
  verified callback.
- Keep the Shopify client secret and store access token on the backend only;
  never send either to the browser, logs, API responses, or Git.
- Enforce unique Shopify-store-to-tenant mapping and reject attempts to attach
  a store that is already connected to a different tenant until an explicit
  transfer/disconnection process exists.

**Tests:** A linked merchant reaches the dashboard; an unlinked merchant is
sent to connect a store; invalid, expired, reused, or mismatched `state` is
rejected; invalid HMAC is rejected; a client-supplied shop domain cannot select
or replace a tenant; and the Shopify access token never appears in responses
or logs.

**Security review:** Confirm that this merchant connection flow is separate
from the public customer-chat widget. OAuth proves store-management
authorization, not legal ownership. Confirm callback CSRF protection through
`state`, signature validation, server-only secrets, and safe token storage.

## Task 5: Create Current User and Current Tenant Dependencies

**Goal:** Build trusted request context from the verified token and linked
application user.

**Required skills:** `supabase:supabase`, `fastapi`,
`codex-security:security-diff-scan`.

**Expected result:** `CurrentUser` contains the application user identity and
role; `CurrentTenant` comes only from that user's stored `tenant_id`.

**Tests:** A request cannot choose or override its tenant through headers,
query parameters, request bodies, or path values.

**Security review:** Fail closed with `401` for invalid identity and `403` only
when a verified user lacks permission.

## Task 6: Enforce Tenant Isolation for Resources

**Goal:** Ensure every tenant-owned resource is accessed through the current
tenant context.

**Required skills:** `fastapi`, `supabase-postgres-best-practices`,
`codex-security:security-diff-scan`.

**Expected result:** Reads, updates, deletes, and related-resource checks use
the current trusted tenant ID for products, orders, sales, campaigns,
documents, chunks, conversations, messages, feedback, permissions, and agent
tools.

**Tests:** A user in Tenant A must not read, update, or delete a resource in
Tenant B. Return `404` for cross-tenant object lookup.

**Security review:** Review every repository method and service operation for
missing tenant predicates or unsafe cross-resource relationships.

## Task 7: Implement RBAC and Permissions for Existing Roles

**Goal:** Enforce documented role- and permission-based access control for
`store_owner`, `admin`, `marketing_manager`, and `team_member`.

**Required skills:** `supabase:supabase`, `fastapi`,
`supabase-postgres-best-practices`, `codex-security:security-diff-scan`.

**Required design:**

- Define a closed `Role` enum and a closed `Permission` enum. Do not use
  unchecked role or permission strings from requests, JWT user metadata, or
  arbitrary database input.
- Use the existing application users and permissions model/table for stored,
  tenant-scoped permission assignments. Enum values are the canonical values
  written to and read from that table.
- Create a documented role-to-permission matrix from the existing role intent
  in `Docs/system-design.md` and protected-route requirements in
  `Docs/api-contract.md`. `store_owner` has all permissions inside its own
  tenant; `admin` is the restricted platform-administration role described in
  the docs; `marketing_manager` and `team_member` receive only their documented
  permissions.
- Every protected operation declares its required `Permission` value. Resolve
  the user, tenant, role, and effective permissions on the backend, then deny
  by default when no rule grants access.

**Reference implementation shape (illustrative only):** The following example
shows the expected closed-enum and explicit-matrix structure. It is not the
application's canonical resource list, permission list, or role list. Task 7
must use the documented roles and protected-route requirements in
`Docs/system-design.md` and `Docs/api-contract.md` instead.

```python
class Permission(StrEnum):
    PRODUCT_READ = "product:read"
    PRODUCT_CREATE = "product:create"
    PRODUCT_UPDATE = "product:update"
    PRODUCT_DELETE = "product:delete"

    USER_INVITE = "user:invite"
    USER_MANAGE = "user:manage"

    ANALYTICS_READ = "analytics:read"


ROLE_PERMISSIONS = {
    UserRole.OWNER: {
        Permission.PRODUCT_READ,
        Permission.PRODUCT_CREATE,
        Permission.PRODUCT_UPDATE,
        Permission.PRODUCT_DELETE,
        Permission.USER_INVITE,
        Permission.USER_MANAGE,
        Permission.ANALYTICS_READ,
    },
    UserRole.ADMIN: {
        Permission.PRODUCT_READ,
        Permission.PRODUCT_CREATE,
        Permission.PRODUCT_UPDATE,
        Permission.PRODUCT_DELETE,
        Permission.USER_INVITE,
        Permission.ANALYTICS_READ,
    },
    UserRole.MANAGER: {
        Permission.PRODUCT_READ,
        Permission.PRODUCT_CREATE,
        Permission.PRODUCT_UPDATE,
        Permission.ANALYTICS_READ,
    },
    UserRole.STAFF: {
        Permission.PRODUCT_READ,
        Permission.PRODUCT_UPDATE,
    },
    UserRole.VIEWER: {
        Permission.PRODUCT_READ,
        Permission.ANALYTICS_READ,
    },
}
```

**Expected result:** Each protected operation has an explicit permission
policy, enforced after identity and tenant resolution. The implementation uses
the existing permissions table rather than accepting permissions from the
frontend. Role and permission values remain type-safe through enums.

**Tests:** Verify every documented role/permission combination against each
relevant sensitive route; verify stored permission records are tenant-scoped;
verify an unknown enum value, a forged role/permission claim, a missing
permission, and a cross-tenant permission record all result in denial (`403`
after a valid authenticated request).

**Security review:** Authorization must run after trusted tenant resolution.
RBAC must not grant cross-tenant access. Review the role-to-permission matrix
against the documentation and confirm no role can create or assign a more
privileged role or permission without an explicit documented rule.

## Deferred Security Work

- Database RLS policies and direct Data API exposure decisions.
- Multi-tenant membership for a single user.
- Public Shopify widget security model, rate limits, and origin validation.
- Upload hardening, RAG web-ingestion SSRF controls, and prompt-injection
  controls.

# Frontend Phase

## Scope

Build the public marketing landing page and the owner-dashboard authentication
screens for AI Commerce Copilot. The approved visual references are the two
images supplied on 2026-09-26:

- **Landing reference:** the long white page with fine emerald contour lines,
  dashboard/knowledge/widget product previews, and a `Log in` link at the
  top-right.
- **Authentication reference:** the centered white login form with the same
  contour-line background and emerald primary action.

The landing page is a product story before sign-in. It introduces the owner
dashboard and then, as the visitor scrolls, explains dashboard intelligence,
knowledge visibility, and the customer-safe Shopify chat widget. The login
screen is for dashboard users only; Shopify storefront customers never create
or use an AI Commerce Copilot account.

This phase must reflect only V1/V2 capabilities documented in
`Docs/requirements.md` and `Docs/system-design.md`. Do not imply autonomous
business actions, billing, Shopify installation, or customer access to private
business data.

## Required skills

- Use `ui-ux-pro-max` before making layout, responsive, accessibility, or
  motion decisions.
- Use `frontend-design` to preserve the intentionally minimal, editorial
  visual language in the approved references rather than falling back to a
  generic SaaS card layout.
- Use `vercel-react-best-practices` for Next.js/React component and image
  delivery decisions.
- Use `webapp-testing` to verify the finished responsive screens and the
  reduced-motion experience.

## Visual contract

- Background: white with numerous extremely thin, low-contrast, organic
  emerald contour lines across the entire surface. The lines are decorative
  only and must never reduce text contrast or readability.
- Palette: Shopify-compatible emerald `#008060` for primary actions and
  intentional accents; deep ink for text; white and quiet neutral-gray
  surfaces. Do not introduce blue, purple, neon, decorative gradients, or
  stock photography.
- Product previews: each preview must be a separate, replaceable image asset.
  Store them as individual files under a clearly named public asset directory
  (for example `frontend/public/images/product/`) and render them with
  Next.js `Image`, with accurate dimensions and useful alt text. Do not bake
  previews into a CSS background, data URI, or one giant landing-page image.
- Copy uses sentence case, plain language, and real V1/V2 product vocabulary:
  products, orders, sales, campaigns, knowledge, internal/public visibility,
  and the customer chat widget.
- Motion is subtle and optional: product previews and their related copy may
  reveal once when they enter the viewport with a small opacity/vertical
  transition. It must not hide content from no-JavaScript users, replay
  distractingly, or run when `prefers-reduced-motion: reduce` is enabled.

## Task 8: Establish frontend visual foundations

**Goal:** Create the shared visual primitives needed to reproduce the approved
landing and authentication designs consistently.

**Required skills:** `ui-ux-pro-max`, `frontend-design`,
`vercel-react-best-practices`.

**Required work:**

- Define reusable color, type, spacing, border, focus, and shadow tokens that
  match the approved references.
- Build the decorative contour-line treatment as a reusable, non-interactive
  background layer. Keep it separate from page content and hide it from
  assistive technology.
- Define a small, consistent set of shared primitives: brand mark, primary
  button, text link, section container, product-preview frame, and form
  field/error/help text styles.
- Preserve a calm, spacious, single-column product story. Avoid repeated
  identical feature cards and unnecessary all-caps eyebrow labels.

**Expected result:** Both pages can use the same green, typography, contour
background, and interaction states without duplicating visual rules.

**Tests and review:** Verify 4.5:1 text contrast where applicable, visible
keyboard focus, and no horizontal overflow at desktop, tablet, or mobile
widths.

## Task 9: Prepare replaceable product-preview image assets

**Goal:** Make every product screenshot shown on the landing page easy to
replace without restructuring the page.

**Required skills:** `vercel-react-best-practices`, `ui-ux-pro-max`.

**Required work:**

- Add separate asset slots/files for the owner dashboard overview, internal
  assistant/data answer, knowledge library, and Shopify storefront chat
  widget. Do not treat the approved reference image as one production asset.
- Create a typed preview-data map that gives each image an `src`, descriptive
  `alt`, aspect ratio, and placement/section owner.
- Reserve image dimensions before loading to prevent layout shift. Use
  responsive sizes and optimized Next.js image delivery.
- Provide an intentional graceful fallback if a non-critical preview image is
  unavailable; do not show a broken-image icon.

**Expected result:** A future designer or developer can replace one product
preview file without editing copy, motion behavior, or page layout.

**Tests and review:** Check every preview at narrow and wide viewports, with
slow loading simulated, to confirm stable layout and legible alt text.

## Task 10: Build the public landing-page shell and hero

**Goal:** Implement the first view of the approved landing page.

**Required skills:** `ui-ux-pro-max`, `frontend-design`,
`vercel-react-best-practices`.

**Required work:**

- Add an airy top bar with the AI Commerce Copilot mark/name on the left and
  a `Log in` link on the far right. The link routes dashboard users to the
  login screen.
- Implement the hero copy exactly as approved: “Grow sales and productivity
  with the data your store already has.”
- Keep the supporting message grounded in the documented product: sales,
  orders, products, and team knowledge brought into one workspace.
- Add one clear `Get started` CTA and the owner-dashboard overview preview
  beneath the copy. Do not add a marketing navigation menu or unsupported
  social-proof claims.

**Expected result:** The top of the page immediately explains the product,
shows the real product surface, and gives dashboard users an obvious login
path.

**Tests and review:** Verify desktop and mobile header behavior, CTA/link
focus states, semantic heading order, and correct image sizing.

## Task 11: Build the dashboard-intelligence story section

**Goal:** Explain the internal assistant’s V1/V2 read-only data experience.

**Required skills:** `ui-ux-pro-max`, `frontend-design`.

**Required work:**

- Add the section headed “Ask the questions behind your numbers.”
- Use the approved supporting idea: “Get clear, accurate answers & decisions
  using your store data.”
- Show the assistant/data-answer preview alongside the content and include
  the documented sources of insight: Products, Orders, Sales, and Campaigns.
- Make it clear through wording and visual hierarchy that this is for
  authenticated internal dashboard users, and that V1/V2 tools are read-only.

**Expected result:** Visitors understand that the assistant helps teams query
real store information without promising unimplemented actions.

**Tests and review:** Confirm the paired copy/image stacks cleanly on mobile
and that the preview remains replaceable through the asset map.

## Task 12: Build the knowledge-visibility story section

**Goal:** Show how teams manage company knowledge safely.

**Required skills:** `ui-ux-pro-max`, `frontend-design`.

**Required work:**

- Add the section headed “One source of truth for your team.”
- Use the knowledge-library preview as its own image asset.
- Explain that dashboard users can upload and organize knowledge, then choose
  whether a document is `Internal` or `Public`.
- Present the visibility distinction clearly: Internal knowledge is available
  to authorized store teams; Public knowledge is allowed for customer-facing
  widget answers. Do not imply that every team role can manage documents.

**Expected result:** The security boundary between private team knowledge and
customer-safe content is understandable without technical jargon.

**Tests and review:** Confirm badges are not differentiated by color alone and
all explanatory text remains readable against the line background.

## Task 13: Build the Shopify customer-widget story section

**Goal:** Explain the second product surface accurately and safely.

**Required skills:** `ui-ux-pro-max`, `frontend-design`.

**Required work:**

- Add the section headed “Helpful answers for customers. Private data stays
  private.”
- Show the Shopify storefront and chat-widget preview as a replaceable image
  asset, distinct from the dashboard previews.
- State the approved V1/V2 limits: public product and policy knowledge only,
  customer-safe answers, and no customer account required.
- Do not show sales, orders, campaigns, internal documents, user data, or
  agent tools anywhere inside the customer widget preview or copy.

**Expected result:** The public storefront widget is presented as useful while
its privacy boundary stays unmistakable.

**Tests and review:** Verify the widget section has no protected-data wording
or imagery and remains usable/readable at mobile widths.

## Task 14: Add scroll reveal and closing conversion path

**Goal:** Give the landing page a composed, calm sense of progression as the
visitor scrolls.

**Required skills:** `ui-ux-pro-max`, `frontend-design`.

**Required work:**

- Reveal each product preview with its associated section content when it
  enters the viewport: a restrained 8–16px upward movement and opacity change
  over roughly 300–400ms. Stagger only closely related elements and keep
  total motion brief.
- Keep all section content visible by default in the server-rendered/no-motion
  state. Respect `prefers-reduced-motion: reduce` by rendering the final state
  immediately.
- Add the approved closing message: “Bring your store’s knowledge and numbers
  together.” Include a `Get started` CTA and a `Log in` link.
- Do not use scroll-jacking, sticky storytelling panels, parallax, or motion
  that blocks reading.

**Expected result:** Scrolling reveals the product screenshots naturally while
the page remains fast, accessible, and fully understandable without motion.

**Tests and review:** Test keyboard scrolling, touch scrolling, a reduced
motion setting, and repeated scroll direction changes without flicker or
layout shift.

## Task 15: Build the dashboard login and registration routes

**Goal:** Implement the approved authentication visual design for dashboard
users without changing the Supabase security contract.

**Required skills:** `ui-ux-pro-max`, `frontend-design`, `supabase:supabase`.

**Required work:**

- Use the approved centered layout with the same white/emerald contour-line
  visual system, a focused authentication card, email field, password field,
  `Forgot password?`, primary `Log in`, and a `Create an account` path.
- Use the approved product positioning: “Turn your store data into clearer,
  faster decisions.” Add the trust statement that business data remains
  private to the team.
- Help dashboard users with the exact message: “Use the email address
  associated with your Shopify store.”
- Implement login, registration, and password-recovery states through
  Supabase Auth only. Do not create a custom password store or suggest this
  page is for storefront customers.
- Include accessible validation, loading, success, error, expired-link, and
  permission-denied states. Keep labels visible; placeholders alone are not
  labels.

**Expected result:** Store teams have a clear, trustworthy entry point into
the owner dashboard, while Shopify customers remain outside this flow.

**Tests and review:** Test keyboard-only completion, password-manager fill,
invalid credentials, reset flow, and mobile form layout. Follow the security
checks in Tasks 1–7 for all live authentication work.

## Task 16: Frontend visual and accessibility acceptance review

**Goal:** Confirm the shipped frontend matches the approved references and
the documented product boundaries.

**Required skills:** `webapp-testing`, `ui-ux-pro-max`,
`vercel-react-best-practices`.

**Acceptance checks:**

- Compare desktop screenshots against both approved references: layout,
  emerald accent, fine contour-line density, whitespace, copy hierarchy, and
  product-preview placement should remain recognizably consistent.
- Validate desktop, tablet, and mobile layouts; no clipped copy, overlap,
  horizontal scrolling, or unreadable line-background interference.
- Verify all product images load as independent replaceable assets with
  dimensions, alt text, and no cumulative layout shift.
- Verify motion is subtle, does not hide content, and is disabled for reduced
  motion.
- Verify the landing page does not promise features outside V1/V2 or expose
  the public widget as an internal dashboard surface.
- Run the frontend build and focused tests before marking the phase complete.
