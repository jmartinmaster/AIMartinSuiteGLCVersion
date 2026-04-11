# Multi-User Migration Assessment

This note remains relevant as future architecture guidance. It is not part of the `2.1.4` release checklist.

## Current `2.1.4` Baseline

- Authentication is still centered on a single admin-oriented vault and session flow.
- Dispatcher access control still relies on protected-module gating instead of per-right authorization.
- Settings Manager can launch security and developer tools, but the app does not yet model separate operator, admin, and developer identities.

## High-Value Target State

- Vault-based user records with role, enabled state, and assigned rights.
- A session object that carries identity, role, rights, and authentication time.
- Rights-based module authorization instead of a small protected-module list.
- Developer-only escalation for repository controls, override trust, and external module tooling.
- A dedicated MVC Security Admin surface that manages vaults without moving policy or persistence into the view layer.

## Recommended Migration Order

1. Introduce security domain models for vaults, roles, rights, and session state.
2. Move authorization decisions to rights-based checks in the security service and dispatcher.
3. Build an MVC Security Admin module for vault CRUD, role defaults, and session status.
4. Add role-filtered login and developer-only escalation flows.
5. Evaluate optional hardware-backed auth only after the core multi-user model is stable.

## Keep From The Earlier Design Work

- Role defaults and role limits to avoid privilege sprawl.
- Non-secure mode as an operational bypass for approved front-facing modules only.
- Clear separation between security policy, credential verification, and UI flow.

## Do Not Carry Forward Directly

- Monolithic legacy security modules that mix persistence, policy, dialogs, and platform-specific auth code.
- Controller or view logic that embeds authorization rules instead of asking the service layer.
- Snapshot-era UI structure as an implementation template; only the behavior goals matter.

## Bottom Line

The next meaningful security step is a service-backed multi-user model with roles and rights, rebuilt inside the current MVC structure. The earlier detailed comparison notes have served their purpose; this file is the condensed forward-looking version.