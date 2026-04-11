# Multi-User Migration Assessment

This note compares the current MVC code in the_golden_standard with the snapshot in newest-main and identifies the multi-user features that are worth porting.

## Current Baseline

- The current app shell already has MVC separation through controllers, models, and views under the_golden_standard.
- The current security flow is still a single-master-password model centered on one .vault file and an admin session.
- Module access in the current dispatcher is enforced by a small protected module list through SecurityService, not by per-user rights.
- Settings Manager still exposes a separate Developer and Admin area outside the security dialog.

## Snapshot Capabilities Worth Bringing Forward

### 1. Replace single-password auth with vault-based identities

Bring over the identity structure from newest-main where each vault is its own record with:

- vault name and display name
- role: general, admin, developer
- enabled flag
- password-required flag
- requires-yubikey flag
- assigned rights list
- created and updated timestamps

Why it matters:

- This is the real multi-user foundation.
- It lets the app distinguish operators from admins and developers instead of treating every authenticated user as the same admin session.

How to fit MVC:

- Add a security model for VaultRecord, AccessRight, and SecuritySession.
- Keep credential storage and verification in a service layer, not in controller or view code.
- Treat the current single master-password flow as a migration source, not as the target design.

### 2. Move from protected-modules to rights-based module access

The current dispatcher checks only whether a module is in a protected list. The snapshot maps visible modules to named rights and uses the active vault session to decide access.

Why it matters:

- It supports true multi-user control instead of one global lock.
- It makes future rules possible, such as a user who can open Production Log and Recovery Viewer but not Settings or Update Manager.

How to fit MVC:

- Replace the simple protected module list in SecurityService with a rights map such as module:production_log, module:layout_manager, and security:manage_vaults.
- Let AppController ask SecurityService for module access decisions before loading a screen.
- Keep the rights definitions in a model or constants module, not in the controller.

### 3. Add explicit role defaults and role limits

The snapshot defines default rights per role and caps on how many general, admin, and developer vaults may exist.

Why it matters:

- It gives predictable bootstrap behavior.
- It prevents accidental privilege sprawl.
- It gives you a controlled multi-user structure instead of ad hoc account creation.

How to fit MVC:

- Store role policy in a security model or policy module.
- Validate limits in the service layer during create, edit, and delete actions.
- Surface validation results through a controller into the dialog view.

### 4. Add a real session object instead of a boolean admin flag

The snapshot session carries vault_name, display_name, role, rights, and authentication time.

Why it matters:

- The current session model is too small for multi-user behavior.
- The dispatcher and settings views need richer session state for status text, access checks, and developer escalation.

How to fit MVC:

- Replace the current authenticated and session_role fields with a session data object managed by the security service.
- Expose read-only helpers such as current_role, current_rights, and session_summary.

### 5. Add role-filtered login flows

The snapshot supports:

- normal vault login
- developer-only login
- role filtering for login dialogs
- reuse of an existing valid session when appropriate

Why it matters:

- This is the cleanest way to require stronger identity only for developer actions.
- It avoids turning every privileged action into a full admin unlock.

How to fit MVC:

- Create a security dialog controller for login prompts.
- Create separate view components for vault selection and credential entry.
- Keep password and YubiKey checks inside the service layer.

### 6. Port the vault manager concept, not the monolithic dialog code

The snapshot Security Admin dialog already covers:

- vault list
- role counts
- rights editing
- enable and disable state
- password rotation
- vault deletion rules
- non-secure mode toggle
- developer login entry point

Why it matters:

- It is the operational UI needed to manage multiple users.
- It centralizes account lifecycle management.

How to fit MVC:

- Create a dedicated SecurityAdminController and SecurityAdminView rather than expanding the existing gatekeeper file further.
- Keep the current Settings Manager action as a launcher only.
- Split the dialog into subviews or helper builders for vault list, vault details, rights panel, session panel, and mode panel.

### 7. Restrict developer-only actions to developer sessions

The snapshot separates developer actions from ordinary admin actions, including developer login and protection around deleting developer vaults.

Why it matters:

- This is one of the strongest structural improvements in the multi-user design.
- It prevents ordinary admin users from silently taking developer-only actions.

How to fit MVC:

- Introduce explicit policy checks such as requires_developer_session for update configuration, external override management, and developer-vault deletion.
- Put those checks in the service layer and surface them through controllers.

### 8. Keep non-secure mode compatible with user roles

The snapshot allows non-secure mode for normal visible modules while still requiring developer login for developer tools.

Why it matters:

- This is a useful operational compromise when the floor needs fast access.
- It avoids opening the most sensitive tools just because user-facing modules are in non-secure mode.

How to fit MVC:

- Preserve the existing non-secure mode concept.
- Narrow its bypass behavior so it only skips module rights for approved front-facing modules.
- Do not let it bypass security administration or developer-only workflows.

## Features To Adapt Carefully

### YubiKey and WebAuthn support

The snapshot includes Windows-native WebAuthn code for developer vault verification.

Recommendation:

- Keep this as an optional second phase.
- If you port it, isolate it behind a platform adapter and service boundary.
- Do not mix platform-specific ctypes logic directly into controllers or dialog-building code.

Reason:

- The current workspace is on Linux.
- The snapshot implementation is tightly tied to Windows APIs and should not become a hard dependency in the core security model.

### Legacy vault import compatibility

The snapshot imports a legacy single .vault hash into a first admin vault automatically.

Recommendation:

- Keep the migration idea, but simplify it.
- Use it only as a one-time upgrade path from the current master-password format.

Reason:

- That solves migration without preserving the old architecture indefinitely.

## Features Not Worth Copying Directly

### 1. The monolithic security.py structure in newest-main

Do not copy this file wholesale.

Reason:

- It mixes persistence, access policy, login flow, security admin UI, developer tools UI, and platform-specific device logic in one module.
- That would cut across the MVC work already done in the_golden_standard.

### 2. Moving developer tools into security without refactoring

The snapshot moved update configuration and external module editing into Security Admin.

Recommendation:

- Keep the idea that these are privileged tools.
- Re-home them in MVC through dedicated controllers and views, not by embedding their UI directly inside the security service.

### 3. Snapshot UI code style

The snapshot dialog code is useful as a behavior reference, but not as implementation structure.

Recommendation:

- Rebuild the behavior using current MVC patterns.
- Use smaller controller methods and view builders instead of nested dialog functions inside the gatekeeper.

## Recommended Migration Order

### Phase 1

- Introduce security domain models for vaults, roles, rights, and session state.
- Expand SecurityService to handle vault CRUD, session state, and rights checks.
- Add migration from the current single .vault to an initial admin vault record.

### Phase 2

- Replace the protected module list with rights-based checks in AppController.
- Add role-filtered login prompts and session summaries.
- Update Settings Manager so it launches security administration but no longer owns developer-tool policy.

### Phase 3

- Add an MVC Security Admin screen for vault management.
- Add developer-only policy checks for update configuration and external override tools.
- Preserve non-secure mode with narrower bypass rules.

### Phase 4

- Consider optional platform-specific strong-auth integrations such as YubiKey after the multi-user model is stable.

## Highest-Value Concrete Changes

If only a subset should move first, these are the best candidates:

1. Vault-based user records
2. Rights-based module authorization
3. Session object with role and rights
4. Security Admin vault manager rebuilt in MVC
5. Developer-only escalation path separated from admin

## Files That Show The Core Gap

- Current single-password security: the_golden_standard/security.py
- Current simple protected-module gateway: the_golden_standard/security_service.py
- Current dispatcher integration: the_golden_standard/controllers/app_controller.py
- Current settings-manager launcher and developer-tools split: the_golden_standard/controllers/settings_manager_controller.py and the_golden_standard/views/settings_manager_view.py
- Snapshot reference implementation: newest-main/modules/security.py
- Snapshot dispatcher-era behavior notes: newest-main/CHANGELOG.md

## Bottom Line

The main reusable update in newest-main is not its exact code. It is the security model: vault identities, roles, rights, session-aware authorization, and developer-only escalation. That model should be reimplemented inside the current MVC structure rather than copied from the monolithic snapshot.