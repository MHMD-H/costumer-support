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

- Create or resolve the application-user row after a verified Supabase signup
  or login. The backend derives `auth_user_id` from the verified JWT `sub`,
  assigns the initial `store_owner` role, and leaves `tenant_id` as `NULL`
  only until Shopify connection succeeds. Never accept an initial role,
  application-user ID, or tenant ID from the frontend.
- Start the OAuth flow only for the authenticated application user; bind a
  short-lived, single-use `state` value to that user on the server.
- Only `store_owner` may initiate Shopify connection. Recheck the stored,
  active user's `store_owner` authority inside the callback before changing a
  tenant or saving a Shopify connection, because the user's role could change
  while the OAuth flow is in progress.
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
or replace a tenant; only `store_owner` can initiate or complete connection;
an unlinked application-user row is created from the verified JWT subject; and
the Shopify access token never appears in responses or logs.

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

**Required execution review:** Audit every repository method and service
operation that reads, updates, deletes, or follows relationships for a
tenant-owned resource. Each object lookup must be tenant-scoped at the
database boundary; an object ID alone is never sufficient. The route must pass
only the trusted `CurrentTenant` value, never a client-selected tenant ID.

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

## Task 8: Secure the Public Shopify Widget

**Goal:** Replace public-widget placeholder validation before the customer
chatbot is exposed outside local development.

**Required skills:** `fastapi`, `supabase-postgres-best-practices`,
`codex-security:security-diff-scan`.

**Required work:** Resolve the tenant through verified store identity and
widget key; enforce allowed storefront origins and rate limits; and limit every
public response, RAG query, and product lookup to customer-safe public data for
the resolved tenant.

**Tests:** Invalid store identity, invalid widget key, disallowed origin, rate
limit exhaustion, and attempts to retrieve internal or another tenant's data
are rejected.

**Security review:** Confirm public widget routes never expose tenant IDs,
internal documents, sales, orders, campaigns, agent tools, or dashboard user
data.

## Task 9: Harden File Upload and Processing

**Goal:** Safely accept, validate, and process merchant-uploaded files.

**Required skills:** `fastapi`, `codex-security:security-diff-scan`.

**Required work:** Enforce upload size limits and an allowlist based on
validated content rather than filename extension alone; safely parse files; and
protect processing from malformed inputs and resource exhaustion. Add malware
scanning if required by the chosen storage and deployment model.

**Tests:** Oversized files, mismatched extensions/content types, malformed
files, and cross-tenant document operations are rejected without leaking data
or exhausting service resources.

**Security review:** Verify uploaded content cannot escape its tenant, trigger
unsafe parsing, or cause unbounded memory, CPU, or storage consumption.

## Task 10: Production Security Hardening

**Goal:** Prepare authentication, database exposure, and operational controls
for production deployment.

**Required skills:** `supabase:supabase`, `fastapi`,
`supabase-postgres-best-practices`, `codex-security:security-diff-scan`.

**Required work:** Decide and implement Supabase RLS and direct Data API
exposure policy; add login/reset brute-force protections, production CORS, and
secure HTTP headers; define session revocation and sensitive-account lifecycle
behavior; add audit logs for Shopify connection, role/permission changes, and
destructive actions; and address RAG web-ingestion SSRF and prompt-injection
controls before enabling untrusted external sources.

**Tests:** Verify RLS policies where applicable, CORS origin restrictions,
rate-limit behavior, secure headers, revoked/disabled account behavior, audit
event creation, and SSRF/prompt-injection defenses for enabled ingestion
sources.

**Security review:** Confirm no Supabase service-role key, Shopify secret, or
other production secret is exposed to clients, logs, source control, or public
error responses.

## Deferred Architecture Decision

- Decide whether a later release needs multi-tenant membership for one user.

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

## Task 11: Establish frontend visual foundations

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

## Task 12: Prepare replaceable product-preview image assets

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

## Task 13: Build the public landing-page shell and hero

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

## Task 14: Build the dashboard-intelligence story section

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

## Task 15: Build the knowledge-visibility story section

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

## Task 16: Build the Shopify customer-widget story section

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

## Task 17: Add scroll reveal and closing conversion path

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

## Task 18: Build the dashboard login and registration routes

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

## Task 19: Frontend visual and accessibility acceptance review

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

# File Upload Phase

## Scope and execution rules

Connect the existing FastAPI document endpoints and document service to the
standalone `rag/` ingestion pipeline. The flow is:

`Document endpoint -> document service -> LangChain RAG pipeline -> PostgreSQL document/chunk records + Chroma vectors`.

- Reuse the existing LangChain loaders, text splitter, embeddings, and Chroma
  adapter in `rag/`. Do not build a second ingestion pipeline in the backend.
- The authenticated application user and trusted current tenant supply user and
  tenant IDs. Never accept either ID from upload input as an authority.
- The PostgreSQL document ID is the single document ID passed through the RAG
  pipeline, chunk records, and vector metadata.
- Complete the applicable upload-safety requirements in Security Task 9 before
  accepting real merchant files. Keep web and Notion ingestion outside the
  upload endpoint until their separate security and source rules are ready.
- Implement one numbered task at a time. After its focused tests and review,
  report the result and **stop for the user's explicit approval** before
  starting the next task, including when crossing into the Chat Phase.

## Task 20: Accept and retain a validated document upload

**Goal:** Make the existing document upload endpoint retain usable file content,
not only create a metadata row.

**Required work:** Check permission and trusted tenant context; validate the
allowed file type against content, enforce a size limit while reading, reject
empty or malformed files safely, and retain the accepted content for processing.
Create the PostgreSQL document record with its trusted uploader ID, tenant ID,
file name, type, visibility, and `uploaded` status. Return its document ID.

**Tests:** Valid TXT upload, unsupported or mismatched type, oversized or empty
file, malformed file, missing permission, and cross-tenant access.

## Task 21: Run the LangChain ingestion pipeline for an uploaded document

**Goal:** Turn an accepted document into clean, indexed chunks using the
existing `rag/` package.

**Required work:** The document service passes the stored file, PostgreSQL
document ID, trusted tenant ID, and visibility into the LangChain loader,
cleaning/normalization, source-aware splitter, embeddings, and Chroma adapter.
Preserve useful headings and page references. Validate that extraction yielded
non-empty usable text. Keep Chroma metadata aligned with the document and
tenant; do not create a second document identity.

**Tests:** Start with TXT, then cover PDF and DOCX, extraction failure,
whitespace-only content, chunk IDs and metadata, and tenant separation.

## Task 22: Persist chunks and track processing results

**Goal:** Make ingestion status and indexed content visible through the
existing document API.

**Required work:** Move status through `uploaded -> processing -> ready` or
`failed`; save chunks and Chroma vector IDs against the same PostgreSQL
document ID. Record a safe failure reason and support retry or replacement
without stale chunks or vectors. Choose processing execution appropriate to
the deployment: FastAPI `BackgroundTasks` only for small, non-critical work;
use a durable worker/queue when processing must survive restarts or handle
large files. A background failure updates status rather than trying to return
an HTTP error after the upload response.

**Tests:** End-to-end upload to `ready`, visible chunks, processing failure,
retry/replacement, restart or worker interruption as applicable, and no
cross-tenant document or vector access.

# Chat Phase

## Scope and execution rules

Replace mock dashboard search and chat responses with retrieval and grounded
answers. The flow is:

`Chat/Search endpoint -> service -> LangChain RAG retrieval -> answer with sources`.

- Reuse the LangChain RAG package and indexed data created by the File Upload
  Phase. Use LangChain for retrieval and the grounded answer chain as well as
  the existing loaders, splitters, embeddings, and Chroma integration. Do not
  add a second search or embedding implementation in route code.
- Resolve tenant and effective permissions on the backend. Retrieval must
  filter by trusted tenant and permitted document visibility before content
  reaches the answer model.
- Keep the public Shopify widget out of this phase until Security Task 8 is
  complete; its retrieval must use public customer-safe content only.
- Implement one numbered task at a time. After its focused tests and review,
  report the result and **stop for the user's explicit approval** before
  starting the next task.

## Task 23: Replace mock knowledge search with tenant-scoped retrieval

**Goal:** Return real indexed document matches from the dashboard search API.

**Required work:** Complete the retrieval components in `rag/` using LangChain
and Chroma, then add a backend service that calls them. Apply tenant and
visibility filters at the vector/database lookup, check the caller's document
permission, and map
matches to the existing search response with document and chunk references.
Preserve separate commerce-data search scopes unless their real data sources
are implemented.

**Tests:** Relevant and irrelevant queries, no matches, missing permission,
internal/public visibility, and cross-tenant retrieval denial.

## Task 24: Generate grounded dashboard answers with sources

**Goal:** Answer questions using only retrieved, authorized evidence.

**Required work:** Add a chat service that retrieves relevant chunks through
the LangChain RAG package, sends those chunks to the configured answer model,
and returns the answer with the exact sources used. Handle insufficient
evidence explicitly. Keep the existing conversation ownership and role checks;
do not expose internal documents to roles without document permission.

**Tests:** Supported answer with correct sources, no-evidence answer, model or
retrieval failure, missing permission, and cross-tenant isolation.

## Task 25: Connect chat endpoints and verify the complete flow

**Goal:** Replace mock dashboard chat and stream output with the grounded chat
service while preserving the existing API contract.

**Required work:** Connect the synchronous and streaming chat endpoints to the
service, return real source references, and keep streamed tokens and final
answer consistent. Verify the journey: upload a document, reach `ready`, ask a
question, and receive a sourced answer. Do not claim the agent-tool mode is
real unless its separate tool integration has been completed.

**Tests:** API response and streaming events, source consistency, conversation
ownership, upload-to-answer integration, failure behavior, and permission and
tenant isolation.
