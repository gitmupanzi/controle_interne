from __future__ import annotations

from io import BytesIO

import pandas as pd

from credit_app.tabs.solution_mpesa import _uploaded_dataframes


class _UploadedExcel:
    def __init__(self, name: str, dataframe: pd.DataFrame) -> None:
        self.name = name
        buffer = BytesIO()
        dataframe.to_excel(buffer, index=False)
        self._content = buffer.getvalue()

    def getvalue(self) -> bytes:
        return self._content


def test_uploaded_dataframes_unifies_files_and_preserves_provenance() -> None:
    files = [
        _UploadedExcel("transactions_a.xlsx", pd.DataFrame({"id": [1], "dr": [100], "cr": [0]})),
        _UploadedExcel("transactions_b.xlsx", pd.DataFrame({"id": [2], "dr": [0], "cr": [50]})),
    ]

    result = _uploaded_dataframes(
        files,
        source_column="fichier_source_transactions_turbo",
    )

    assert result["id"].tolist() == [1, 2]
    assert result["fichier_source_transactions_turbo"].tolist() == [
        "transactions_a.xlsx",
        "transactions_b.xlsx",
    ]
    assert result["ordre_fichier_import"].tolist() == [0, 1]
