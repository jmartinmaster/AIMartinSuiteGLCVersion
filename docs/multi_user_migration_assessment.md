# Multi-User Migration Assessment

Status: Active implementation status and remaining decisions.

This note tracks current delivery status for the multi-user security migration. It remains separate from the completed PyQt6 host migration plan and should be used as security-feature planning and implementation guidance.

## Current `2.2.7` Status

### Completed in code

- Vault-based user records are implemented with role, enabled state, password policy, and assigned rights (`VaultRecord`).
- Session state is implemented with identity, role, rights, and authentication timestamp (`SecuritySession`).
- Role defaults and role limits are implemented for `general`, `admin`, and `developer` vaults.
- Security administration is available through the dedicated MVC `security_admin` module surface.
- Vault CRUD and password lifecycle operations are implemented and routed through the service-backed security flow.
- Role-filtered authentication and developer-only elevation patterns are implemented for privileged modules.
- Authorization checks are now rights-aware for privileged module rights (`security:*` and `developer:*`) in `SecurityService.requires_authentication()`.
- Rights are now enforced for all user-facing modules that map to a module access right.
- Non-secure mode now remains available with an admin-managed module bypass list instead of broad global module bypass.
- Native device verification has been removed from login and vault policy.
- Password policy is enforced for all vaults: minimum 8 characters, at least 2 uppercase letters, and at least 1 special character from `!@#$%^&*().`.
- Role default rights can now be updated by developer sessions only.

### Still open to complete full migration

- Validate end-to-end UI behavior in packaged and source runs for the new non-secure bypass module selector.
- Optional follow-up: provide explicit UI affordances for developer-managed role-default editing workflow guidance and audit logging.

## Policy Decisions (Finalized)

1. `module:*` rights are required for all user-facing modules.
2. Non-secure mode remains available, but bypass applies only to admin-selected modules.
3. Native device verification is removed.
4. Passwords are required for all vault roles with a strict complexity rule.
5. Existing role-default access sets remain the baseline, with developer-only ability to change defaults.

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

The core multi-user model is now implemented in the live MVC architecture. The remaining work is policy finalization and rollout scope: whether to enforce rights on all modules or keep mixed-mode access for operator-facing flows.

Planning note: treat this document as an active implementation tracker until the open policy inputs above are finalized.