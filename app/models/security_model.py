from dataclasses import dataclass, field


GENERAL_USER_LIMIT = 9
ADMIN_USER_LIMIT = 3
DEVELOPER_USER_LIMIT = 1
PBKDF2_ITERATIONS = 600000

ROLE_LIMITS = {
    "general": GENERAL_USER_LIMIT,
    "admin": ADMIN_USER_LIMIT,
    "developer": DEVELOPER_USER_LIMIT,
}

MODULE_ACCESS_RIGHTS = {
    "production_log": "module:production_log",
    "layout_manager": "module:layout_manager",
    "rate_manager": "module:rate_manager",
    "settings_manager": "module:settings_manager",
    "update_manager": "module:update_manager",
    "recovery_viewer": "module:recovery_viewer",
    "help_viewer": "module:help_viewer",
    "about": "module:about",
}


@dataclass(frozen=True)
class AccessRight:
    key: str
    label: str
    description: str


ACCESS_RIGHTS = (
    AccessRight("module:production_log", "Production Log", "Open and use Production Log."),
    AccessRight("module:layout_manager", "Layout Manager", "Open and use Layout Manager."),
    AccessRight("module:rate_manager", "Rate Manager", "Open and use Rate Manager."),
    AccessRight("module:settings_manager", "Settings Manager", "Open and use Settings Manager."),
    AccessRight("module:update_manager", "Update Manager", "Open and use Update Manager."),
    AccessRight("module:recovery_viewer", "Recovery Viewer", "Open and use Recovery Viewer."),
    AccessRight("module:help_viewer", "Help Center", "Open the Help Center."),
    AccessRight("module:about", "About", "Open the About screen."),
    AccessRight("security:manage_vaults", "Security Admin", "Manage vaults, passwords, and security mode."),
    AccessRight("developer:update_configuration", "Update Configuration", "Change privileged update repository settings."),
    AccessRight("developer:external_module_overrides", "External Module Overrides", "Manage privileged external module overrides."),
)

ACCESS_RIGHTS_BY_KEY = {entry.key: entry for entry in ACCESS_RIGHTS}
ALL_ACCESS_RIGHT_KEYS = [entry.key for entry in ACCESS_RIGHTS]

ROLE_DEFAULT_RIGHTS = {
    "general": [MODULE_ACCESS_RIGHTS["production_log"]],
    "admin": [
        MODULE_ACCESS_RIGHTS["production_log"],
        MODULE_ACCESS_RIGHTS["layout_manager"],
        MODULE_ACCESS_RIGHTS["rate_manager"],
        MODULE_ACCESS_RIGHTS["settings_manager"],
        MODULE_ACCESS_RIGHTS["update_manager"],
        MODULE_ACCESS_RIGHTS["recovery_viewer"],
        MODULE_ACCESS_RIGHTS["help_viewer"],
        MODULE_ACCESS_RIGHTS["about"],
        "security:manage_vaults",
    ],
    "developer": list(ALL_ACCESS_RIGHT_KEYS),
}


def normalize_role(role):
    role_key = str(role or "general").strip().lower()
    return role_key if role_key in ROLE_LIMITS else "general"


def role_requires_password(role):
    return normalize_role(role) in {"admin", "developer"}


def normalize_rights(rights, role=None):
    normalized = []
    if isinstance(rights, str):
        rights = [part.strip() for part in rights.split(",")]
    if not isinstance(rights, (list, tuple, set)):
        rights = []
    for right in rights:
        right_key = str(right or "").strip()
        if right_key in ACCESS_RIGHTS_BY_KEY and right_key not in normalized:
            normalized.append(right_key)
    if normalize_role(role) == "developer":
        return list(ALL_ACCESS_RIGHT_KEYS)
    return normalized


@dataclass
class VaultRecord:
    vault_name: str
    display_name: str
    role: str
    enabled: bool = True
    password_required: bool = True
    requires_yubikey: bool = False
    rights: list[str] = field(default_factory=list)
    hash_scheme: str = "pbkdf2_sha256"
    password_hash: str = ""
    password_salt: str = ""
    password_iterations: int = PBKDF2_ITERATIONS
    created_at: str | None = None
    updated_at: str | None = None
    version: int = 2
    path: str | None = None

    @classmethod
    def from_payload(cls, payload, path=None):
        role = normalize_role(payload.get("role"))
        display_name = str(payload.get("display_name") or payload.get("vault_name") or "").strip() or str(payload.get("vault_name") or "")
        return cls(
            vault_name=str(payload.get("vault_name") or "").strip(),
            display_name=display_name,
            role=role,
            enabled=bool(payload.get("enabled", True)),
            password_required=bool(payload.get("password_required", role_requires_password(role))),
            requires_yubikey=bool(payload.get("requires_yubikey", False)),
            rights=normalize_rights(payload.get("rights", ROLE_DEFAULT_RIGHTS.get(role, [])), role=role),
            hash_scheme=str(payload.get("hash_scheme", "pbkdf2_sha256") or "pbkdf2_sha256"),
            password_hash=str(payload.get("password_hash", "") or ""),
            password_salt=str(payload.get("password_salt", "") or ""),
            password_iterations=int(payload.get("password_iterations", PBKDF2_ITERATIONS) or PBKDF2_ITERATIONS),
            created_at=payload.get("created_at"),
            updated_at=payload.get("updated_at"),
            version=int(payload.get("version", 2) or 2),
            path=path,
        )

    def to_payload(self):
        return {
            "version": int(self.version),
            "vault_name": self.vault_name,
            "display_name": self.display_name,
            "role": normalize_role(self.role),
            "enabled": bool(self.enabled),
            "password_required": bool(self.password_required),
            "requires_yubikey": bool(self.requires_yubikey),
            "rights": normalize_rights(self.rights, role=self.role),
            "hash_scheme": self.hash_scheme,
            "password_hash": self.password_hash,
            "password_salt": self.password_salt,
            "password_iterations": int(self.password_iterations or PBKDF2_ITERATIONS),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class SecuritySession:
    vault_name: str
    display_name: str
    role: str
    rights: list[str] = field(default_factory=list)
    authenticated_at: str | None = None

    def has_right(self, right_key):
        if not right_key:
            return True
        return right_key in self.rights
