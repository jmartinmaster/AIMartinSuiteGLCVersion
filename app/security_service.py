from app.models.security_model import MODULE_ACCESS_RIGHTS
from app.security import gatekeeper


class SecurityService:
    def __init__(self, protected_modules=None, module_access_rights=None):
        self.protected_modules = set(protected_modules or [])
        self.module_access_rights = dict(MODULE_ACCESS_RIGHTS)
        if module_access_rights:
            self.module_access_rights.update(module_access_rights)

    def get_session(self):
        return gatekeeper.get_session()

    def get_session_summary(self):
        return gatekeeper.get_session_summary()

    def get_module_access_right(self, module_name):
        return self.module_access_rights.get(module_name)

    def requires_authentication(self, module_name):
        return module_name in self.protected_modules

    def has_right(self, right_key):
        return gatekeeper.has_right(right_key)

    def can_access_module(self, module_name):
        if not self.requires_authentication(module_name):
            return True
        if self.is_non_secure_mode_enabled():
            return True
        required_right = self.get_module_access_right(module_name)
        return gatekeeper.has_right(required_right)

    def is_module_visible(self, module_name):
        if not self.requires_authentication(module_name):
            return True
        if self.is_non_secure_mode_enabled():
            return True
        if self.get_session() is None:
            return True
        return self.can_access_module(module_name)

    def has_admin_session(self):
        return gatekeeper.has_admin_session()

    def is_non_secure_mode_enabled(self):
        return gatekeeper.is_non_secure_mode_enabled()

    def is_external_module_override_trust_enabled(self):
        return gatekeeper.is_external_module_override_trust_enabled()

    def authenticate_module(self, module_name, parent=None, reason=None, force_reauth=False):
        if not self.requires_authentication(module_name):
            return True
        if self.is_non_secure_mode_enabled():
            return True
        required_right = self.get_module_access_right(module_name)
        prompt_reason = reason or f"Unlock {str(module_name).replace('_', ' ').title()} to continue."
        return gatekeeper.authenticate(
            required_right=required_right,
            parent=parent,
            reason=prompt_reason,
            force_reauth=force_reauth,
        )