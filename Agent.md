# Security Phase Agent Instructions

## Mission

Implement the Security Phase tasks in `Task.md` sequentially. Treat the
repository's current architecture as the baseline. Make only the smallest
necessary change for the active task.

## Non-Negotiable Rules

- Do not redesign the architecture.
- Do not refactor unrelated code.
- Do not change unrelated APIs, database tables, routes, or configuration.
- Do not introduce over-engineering or future-only abstractions.
- Do not implement deferred tasks unless the user explicitly requests them.
- Do not expose secrets, service-role keys, JWTs, passwords, or database URLs.
- Do not use JWT user metadata as an authorization source.
- Do not use client-provided tenant IDs to select tenant data.
- Preserve existing behavior unless the active security task intentionally
  changes it.

## Workflow for Every Task

1. Read the task in `Task.md` and inspect only relevant implementation,
   configuration, database, and test files.
2. State the exact security problem and the smallest proposed change.
3. Implement only the approved task.
4. Add or update focused tests for successful and failure cases.
5. Run the relevant tests.
6. Perform a security review of the changed behavior.
7. Report changed files, tests run, security outcome, and remaining risks.
8. Stop and wait for approval before beginning the next task.

## Required Prompts by Task

### Task 1: Supabase Authentication

Use Supabase Auth for authentication only. Keep passwords and session issuance
inside Supabase. Do not expose service-role credentials to the frontend.

### Task 2: JWT Verification

Get the access token only from the `Authorization: Bearer <token>` header using
FastAPI security dependencies. Verify the Supabase JWT cryptographically,
including signature, issuer, audience, and expiry. Extract `sub` only after
successful verification. Reject invalid tokens with `401`.

### Task 3: Application User Link

Use verified `sub` to find `public.users.auth_user_id`. Ensure the identity
relation is enforced by a foreign key to `auth.users.id`. Do not derive role or
tenant from editable user metadata.

### Task 4: Current Request Context

Create trusted current-user and current-tenant dependencies. Derive tenant ID
only from the resolved application user. Never accept a tenant ID from the
client as authority.

### Task 5: Tenant Isolation

Apply the trusted tenant context to every tenant-owned resource lookup and
mutation. Cross-tenant object access must behave as not found (`404`) rather
than revealing that a resource exists.

### Task 6: RBAC

Apply explicit role checks after identity and tenant resolution. Start with the
existing roles. Do not build a generic permission engine unless a defined task
requires it.

## Test Standard

Every task needs both positive and negative tests. Security-sensitive tests
must include unauthorized, malformed, expired, cross-tenant, and
insufficient-role cases when relevant. A task is incomplete if its focused
tests do not pass.

## Security Review Standard

After each task, verify that the change does not introduce token leakage,
privilege escalation, IDOR/BOLA, tenant escape, secret exposure, or weakened
error handling. Clearly label any remaining limitation or deferred decision.
