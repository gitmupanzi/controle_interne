from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from credit_app.security import SecretConfigurationError, SqlServerSettings, load_streamlit_sql_settings


def test_windows_authentication_is_encrypted_by_default() -> None:
    settings = SqlServerSettings.from_mapping({"server": "SQL01", "database": "BB_VISION_PRO"})

    connection_string = settings.odbc_connection_string()

    assert "Encrypt=yes" in connection_string
    assert "TrustServerCertificate=no" in connection_string
    assert "ApplicationIntent=ReadOnly" in connection_string
    assert "Trusted_Connection=yes" in connection_string


def test_sql_password_is_never_exposed_by_safe_summary() -> None:
    settings = SqlServerSettings.from_mapping(
        {
            "server": "SQL01",
            "database": "BB_VISION_PRO",
            "trusted_connection": False,
            "username": "auditeur",
            "password": "secret;avec-accolade}",
        }
    )

    summary = settings.safe_summary()

    assert summary["username"] == "***"
    assert summary["password"] == "***"
    assert "secret" not in str(summary)
    assert "PWD={secret;avec-accolade}}};" in settings.odbc_connection_string()


def test_unencrypted_connection_is_rejected() -> None:
    with pytest.raises(SecretConfigurationError, match="chiffrement"):
        SqlServerSettings.from_mapping({"server": "SQL01", "database": "BB_VISION_PRO", "encrypt": False})


def test_incomplete_sql_authentication_is_rejected() -> None:
    with pytest.raises(SecretConfigurationError, match="ensemble"):
        SqlServerSettings.from_mapping(
            {
                "server": "SQL01",
                "database": "BB_VISION_PRO",
                "trusted_connection": False,
                "username": "auditeur",
            }
        )


def test_environment_configuration_does_not_require_a_dotenv_file() -> None:
    values = {
        "VISION_SQL_SERVER": "SQL01",
        "VISION_SQL_DATABASE": "BB_VISION_PRO",
        "VISION_SQL_TRUSTED_CONNECTION": "oui",
    }
    with patch.dict(os.environ, values, clear=True):
        settings = SqlServerSettings.from_environment()

    assert settings.server == "SQL01"
    assert settings.trusted_connection is True


def test_streamlit_secret_section_is_required() -> None:
    with pytest.raises(SecretConfigurationError, match="sql_perfect_vision"):
        load_streamlit_sql_settings({})
