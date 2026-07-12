from __future__ import annotations

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis" / "line_list_quality.ipynb"


notebook = nbf.v4.new_notebook()
notebook["metadata"]["kernelspec"] = {
    "display_name": "Python 3",
    "language": "python",
    "name": "python3",
}
notebook["metadata"]["language_info"] = {"name": "python", "version": "3.13"}
notebook["cells"] = [
    nbf.v4.new_markdown_cell(
        """# Qualité des fichiers `line_list`

## tl;dr

Ce notebook inventorie les fichiers de test par cycle sans afficher de ligne, de nom, de téléphone, de compte ou de donnée KYC. Les conclusions sont calculées après l'exécution complète du notebook.
"""
    ),
    nbf.v4.new_markdown_cell(
        """## Context & Methods

L'unité d'analyse est un fichier Excel. La première feuille est profilée comme parcours par défaut ; toutes les feuilles disponibles sont inventoriées. Les contrôles couvrent la forme, la complétude, les doublons exacts, les dates et montants non convertibles, la couverture du référentiel du cycle et le pipeline de standardisation existant.

### Key Assumptions

- Le cycle est déterminé en priorité par le nom du fichier, puis par les en-têtes.
- Les champs `expected_columns` constituent une couverture attendue, pas une règle bloquante.
- Aucun échantillon de ligne ni valeur d'identification n'est conservé dans les sorties.
"""
    ),
    nbf.v4.new_code_cell(
        """from pathlib import Path
import json
import sys

import pandas as pd
from openpyxl.utils.cell import range_boundaries
from zipfile import ZipFile
from xml.etree import ElementTree as ET

ROOT = Path.cwd()
if ROOT.name == 'analysis':
    ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from credit_app.app_loader import load_dataframe_from_path
from credit_app.cycles import get_cycle_spec, list_cycle_keys
from credit_app.services.data_pipeline import detect_cycle, prepare_payload_from_dataframe

LINE_LIST = ROOT / 'line_list'
REPORTS = ROOT / 'reports'
REPORTS.mkdir(exist_ok=True)
files = sorted(path for path in LINE_LIST.rglob('*') if path.is_file() and not path.name.startswith('~$'))
len(files)"""
    ),
    nbf.v4.new_markdown_cell("## Data\n\n### 1. Profile metadata and aggregate quality checks"),
    nbf.v4.new_code_cell(
        """DATE_TOKENS = ('date', 'maturity', 'created_at', 'updated_at')
AMOUNT_TOKENS = ('montant', 'solde', 'encours', 'balance', 'debit')
CURRENCY_TOKENS = ('devise', 'currency')

def invalid_conversion_count(series, kind):
    non_empty = series.notna() & series.astype('string').str.strip().ne('')
    if kind == 'date':
        converted = pd.to_datetime(series, errors='coerce')
    else:
        if pd.api.types.is_numeric_dtype(series):
            return 0
        cleaned = series.astype('string').str.replace('\\u00a0', '', regex=False).str.replace(' ', '', regex=False).str.replace(',', '.', regex=False)
        converted = pd.to_numeric(cleaned, errors='coerce')
    return int((non_empty & converted.isna()).sum())

def workbook_metadata(path):
    main_ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rel_ns = 'http://schemas.openxmlformats.org/package/2006/relationships'
    office_rel = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    with ZipFile(path) as archive:
        workbook_root = ET.fromstring(archive.read('xl/workbook.xml'))
        rel_root = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets = {node.attrib['Id']: node.attrib['Target'] for node in rel_root.findall(f'{{{rel_ns}}}Relationship')}
        sheets = []
        dimensions = {}
        for node in workbook_root.findall(f'.//{{{main_ns}}}sheet'):
            name = node.attrib['name']
            relation_id = node.attrib[f'{{{office_rel}}}id']
            target = targets[relation_id].lstrip('/')
            member = target if target.startswith('xl/') else f'xl/{target}'
            prefix = archive.open(member).read(8192).decode('utf-8', errors='ignore')
            match = __import__('re').search(r'<dimension[^>]+ref="([^"]+)"', prefix)
            if match:
                _, _, max_col, max_row = range_boundaries(match.group(1))
                dimensions[name] = {'rows_with_header': max_row, 'columns': max_col}
            sheets.append(name)
    return sheets, dimensions

records = []
for path in files:
    relative_name = str(path.relative_to(ROOT))
    record = {'file': relative_name, 'format': path.suffix.lower(), 'size_bytes': path.stat().st_size}
    try:
        sheets, dimensions = workbook_metadata(path)
        record['sheets'] = sheets
        active_sheet = sheets[0] if sheets else None
        large_file = path.stat().st_size > 1 * 1024 * 1024
        frame = (
            pd.read_excel(path, sheet_name=active_sheet, nrows=2000)
            if large_file
            else load_dataframe_from_path(path, active_sheet, reject_empty=False)
        )
        detection = detect_cycle(path.name, frame.columns)
        dimension = dimensions.get(active_sheet, {})
        estimated_rows = max(int(dimension.get('rows_with_header', len(frame) + 1)) - 1, 0)
        record.update({
            'active_sheet': active_sheet,
            'cycle': detection.cycle_key or 'ambigu',
            'cycle_confidence': detection.confidence,
            'rows': estimated_rows if large_file else int(len(frame)),
            'profiled_rows': int(len(frame)),
            'profile_scope': 'sample_2000' if large_file else 'full',
            'columns': int(dimension.get('columns', frame.shape[1])),
            'headers': [str(column) for column in frame.columns],
            'dtypes': {str(column): str(dtype) for column, dtype in frame.dtypes.items()},
            'exact_duplicates': int(frame.duplicated().sum()),
            'null_cells': int(frame.isna().sum().sum()),
            'null_rate': float(frame.isna().sum().sum() / max(frame.size, 1)),
        })
        date_columns = []
        for column in frame.columns:
            column_key = str(column).casefold().strip().replace(' ', '_')
            if (
                column_key == 'date'
                or column_key.startswith('date_')
                or column_key.endswith('_date')
                or column_key in {'created_at', 'updated_at', 'maturity_date'}
            ):
                date_columns.append(column)
        amount_columns = []
        for column in frame.columns:
            column_key = str(column).casefold().strip()
            excluded_amount_label = any(
                token in column_key
                for token in ('tranche', 'classe', 'type', 'nom', 'date', 'mois', 'numero', 'code')
            )
            if (
                (any(token in column_key for token in AMOUNT_TOKENS) and not excluded_amount_label)
                or column_key in {'dr', 'cr', 'debit', 'credit'}
            ):
                amount_columns.append(column)
        currency_columns = [column for column in frame.columns if any(token in str(column).casefold() for token in CURRENCY_TOKENS)]
        record['invalid_dates'] = sum(invalid_conversion_count(frame[column], 'date') for column in date_columns)
        record['invalid_amounts'] = sum(invalid_conversion_count(frame[column], 'number') for column in amount_columns)
        record['currencies'] = sorted({
            str(value).strip().upper()
            for column in currency_columns
            for value in frame[column].dropna().unique()[:20]
            if str(value).strip().upper() in {'CDF', 'USD', '1', '2'}
        })
        valid_dates = []
        for column in date_columns:
            valid_dates.extend(pd.to_datetime(frame[column], errors='coerce').dropna().tolist())
        record['period_start'] = min(valid_dates).isoformat() if valid_dates else None
        record['period_end'] = max(valid_dates).isoformat() if valid_dates else None

        payload = prepare_payload_from_dataframe(frame)
        standardized = payload['standardized_df']
        if detection.cycle_key in list_cycle_keys():
            expected = list(get_cycle_spec(detection.cycle_key).get('expected_columns', []))
        else:
            expected = []
        record['missing_expected'] = [column for column in expected if column not in standardized.columns]
        record['extra_columns'] = [str(column) for column in standardized.columns if column not in expected]
        record['quality_alerts'] = int(payload['quality_df']['nombre_lignes'].sum()) if not payload['quality_df'].empty else 0
        record['status'] = 'ok'
    except Exception as exc:
        record.update({'status': 'error', 'error_type': type(exc).__name__, 'error': str(exc)[:500]})
    records.append(record)

inventory = pd.DataFrame(records)
safe_inventory_path = REPORTS / 'line_list_quality_inventory.json'
safe_inventory_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
inventory[['file', 'cycle', 'rows', 'columns', 'status']].head(10)"""
    ),
    nbf.v4.new_markdown_cell("## Results\n\n### 2. Coverage by detected cycle"),
    nbf.v4.new_code_cell(
        """cycle_summary = (
    inventory.groupby('cycle', dropna=False)
    .agg(
        files=('file', 'count'),
        rows=('rows', 'sum'),
        sampled_files=('profile_scope', lambda values: int((values == 'sample_2000').sum())),
        errors=('status', lambda values: int((values != 'ok').sum())),
        exact_duplicates=('exact_duplicates', 'sum'),
        invalid_dates=('invalid_dates', 'sum'),
        invalid_amounts=('invalid_amounts', 'sum'),
        quality_alerts=('quality_alerts', 'sum'),
    )
    .reset_index()
    .sort_values(['errors', 'files'], ascending=[False, False])
)
cycle_summary"""
    ),
    nbf.v4.new_markdown_cell("### 3. Highest-signal file-level findings"),
    nbf.v4.new_code_cell(
        """issue_columns = ['file', 'cycle', 'rows', 'columns', 'null_rate', 'exact_duplicates', 'invalid_dates', 'invalid_amounts', 'quality_alerts', 'status']
issues = inventory.loc[
    inventory['status'].ne('ok')
    | inventory['exact_duplicates'].fillna(0).gt(0)
    | inventory['invalid_dates'].fillna(0).gt(0)
    | inventory['invalid_amounts'].fillna(0).gt(0)
    | inventory['quality_alerts'].fillna(0).gt(0),
    issue_columns,
].copy()
issues.sort_values(['status', 'quality_alerts', 'exact_duplicates'], ascending=[True, False, False]).head(20)"""
    ),
    nbf.v4.new_markdown_cell("### 4. Privacy and reproducibility checks"),
    nbf.v4.new_code_cell(
        """assert not any(key in inventory.columns for key in ['sample', 'preview', 'records'])
assert all(Path(name).parts[0] == 'line_list' for name in inventory['file'])
privacy_check = {
    'raw_rows_exported': 0,
    'profiled_files': int(len(inventory)),
    'successful_files': int(inventory['status'].eq('ok').sum()),
    'failed_files': int(inventory['status'].ne('ok').sum()),
    'inventory_path': str(safe_inventory_path.relative_to(ROOT)),
}
privacy_check"""
    ),
    nbf.v4.new_markdown_cell(
        """## Takeaways

- L'inventaire JSON contient uniquement les noms de fichiers, feuilles, schémas, types et agrégats de qualité.
- Les erreurs de lecture ou de préparation sont conservées avec leur type et un message borné.
- Les champs attendus manquants sont des avertissements de couverture ; seules les validations explicites de schéma doivent bloquer les calculs métier.
"""
    ),
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(notebook, OUTPUT)
print(OUTPUT)
