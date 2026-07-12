from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Mapping


class SecretConfigurationError(ValueError):
    """Configuration secrète absente, incohérente ou insuffisamment sûre."""


def _as_bool(value: object, *, default: bool) -> bool:
    if value is None or str(value).strip() == "":
        return default
    normalized = str(value).strip().casefold()
    if normalized in {"1", "true", "vrai", "yes", "oui", "on"}:
        return True
    if normalized in {"0", "false", "faux", "no", "non", "off"}:
        return False
    raise SecretConfigurationError(f"Valeur booléenne invalide : {value!r}.")


def _as_timeout(value: object, *, default: int = 15) -> int:
    if value is None or str(value).strip() == "":
        return default
    try:
        timeout = int(value)
    except (TypeError, ValueError) as exc:
        raise SecretConfigurationError("Le délai SQL doit être un entier.") from exc
    if not 1 <= timeout <= 120:
        raise SecretConfigurationError("Le délai SQL doit être compris entre 1 et 120 secondes.")
    return timeout


def _odbc_value(value: str) -> str:
    """Protéger une valeur ODBC, y compris les points-virgules et accolades."""
    return "{" + value.replace("}", "}}") + "}"


def _text(value: object, *, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


@dataclass(frozen=True)
class SqlServerSettings:
    server: str
    database: str
    driver: str = "ODBC Driver 18 for SQL Server"
    trusted_connection: bool = True
    username: str | None = None
    password: str | None = None
    encrypt: bool = True
    trust_server_certificate: bool = False
    timeout_seconds: int = 15

    def __post_init__(self) -> None:
        if not self.server.strip() or not self.database.strip():
            raise SecretConfigurationError("Le serveur et la base SQL sont obligatoires.")
        if not self.driver.strip():
            raise SecretConfigurationError("Le pilote ODBC est obligatoire.")
        if bool(self.username) != bool(self.password):
            raise SecretConfigurationError("Le nom d'utilisateur et le mot de passe SQL doivent être fournis ensemble.")
        if self.trusted_connection and (self.username or self.password):
            raise SecretConfigurationError("Choisir l'authentification Windows ou SQL, pas les deux.")
        if not self.trusted_connection and not (self.username and self.password):
            raise SecretConfigurationError("L'authentification SQL exige un nom d'utilisateur et un mot de passe.")
        if not self.encrypt:
            raise SecretConfigurationError("La connexion SQL doit utiliser le chiffrement.")
        if not 1 <= self.timeout_seconds <= 120:
            raise SecretConfigurationError("Le délai SQL doit être compris entre 1 et 120 secondes.")

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "SqlServerSettings":
        return cls(
            server=_text(values.get("server")),
            database=_text(values.get("database")),
            driver=_text(values.get("driver"), default="ODBC Driver 18 for SQL Server"),
            trusted_connection=_as_bool(values.get("trusted_connection"), default=True),
            username=_text(values.get("username")) or None,
            password=_text(values.get("password")) or None,
            encrypt=_as_bool(values.get("encrypt"), default=True),
            trust_server_certificate=_as_bool(values.get("trust_server_certificate"), default=False),
            timeout_seconds=_as_timeout(values.get("timeout_seconds")),
        )

    @classmethod
    def from_environment(cls, prefix: str = "VISION_SQL_") -> "SqlServerSettings":
        keys = {
            "server": "SERVER",
            "database": "DATABASE",
            "driver": "DRIVER",
            "trusted_connection": "TRUSTED_CONNECTION",
            "username": "USERNAME",
            "password": "PASSWORD",
            "encrypt": "ENCRYPT",
            "trust_server_certificate": "TRUST_SERVER_CERTIFICATE",
            "timeout_seconds": "TIMEOUT_SECONDS",
        }
        return cls.from_mapping({name: os.getenv(prefix + suffix) for name, suffix in keys.items()})

    def odbc_connection_string(self) -> str:
        parts = [
            f"DRIVER={_odbc_value(self.driver)}",
            f"SERVER={_odbc_value(self.server)}",
            f"DATABASE={_odbc_value(self.database)}",
            f"Encrypt={'yes' if self.encrypt else 'no'}",
            f"TrustServerCertificate={'yes' if self.trust_server_certificate else 'no'}",
            "ApplicationIntent=ReadOnly",
            f"Connection Timeout={self.timeout_seconds}",
        ]
        if self.trusted_connection:
            parts.append("Trusted_Connection=yes")
        else:
            parts.extend((f"UID={_odbc_value(self.username or '')}", f"PWD={_odbc_value(self.password or '')}"))
        return ";".join(parts) + ";"

    def safe_summary(self) -> dict[str, object]:
        """Retourner uniquement les paramètres pouvant être journalisés."""
        return {
            "server": self.server,
            "database": self.database,
            "driver": self.driver,
            "authentication": "Windows" if self.trusted_connection else "SQL",
            "username": "***" if self.username else None,
            "password": "***" if self.password else None,
            "encrypt": self.encrypt,
            "trust_server_certificate": self.trust_server_certificate,
            "timeout_seconds": self.timeout_seconds,
        }


def load_streamlit_sql_settings(secrets: Mapping[str, Any]) -> SqlServerSettings:
    section = secrets.get("sql_perfect_vision")
    if not isinstance(section, Mapping):
        raise SecretConfigurationError("La section [sql_perfect_vision] est absente des secrets Streamlit.")
    return SqlServerSettings.from_mapping(section)
