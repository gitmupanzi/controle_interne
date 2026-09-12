"""Régression du taux exporté et test optionnel des classeurs locaux, en lecture seule."""
from io import BytesIO
import os
from pathlib import Path
import unittest

import pandas as pd
from docx import Document

from credit_app.services.mpesa_analysis import (
    MpesaPreparedData,
    build_mpesa_customer_period_summary,
    build_mpesa_recent_customer_activity_summary,
    create_excel_export,
    create_g2_dat_word,
    normalize_phone,
    prepare_customers,
    prepare_transactions,
)


def prepared(transactions, customers):
    return MpesaPreparedData(
        transactions=pd.DataFrame(transactions), customers=pd.DataFrame(customers),
        current_savings=pd.DataFrame(), fixed_savings=pd.DataFrame(),
        loans=pd.DataFrame(), load_report=pd.DataFrame(),
    )


class RecentCustomerTests(unittest.TestCase):
    def test_reference_rate_and_distinct_phones_across_currencies(self):
        tx, customers = [], []
        for i in range(231):
            phone = f"24381{i:07d}"
            for currency in ("CDF", "USD"):
                tx.append(dict(msisdn1=phone, created_at="2026-09-11 12:00:00", currency_code=currency))
            customers.append(dict(msisdn1=phone, created_at="2026-09-01" if i < 99 else "2026-01-01"))
        data = prepared(tx, customers)
        original = data.transactions.copy(deep=True)
        result = build_mpesa_recent_customer_activity_summary(data)
        self.assertEqual(result.iloc[0].valeur, "42.86 % (99 / 231)")
        self.assertEqual(result.iloc[1].valeur, 0)
        pd.testing.assert_frame_equal(original, data.transactions)

    def test_inclusive_30_days_negative_age_missing_and_duplicate_creation(self):
        instant = pd.Timestamp("2026-09-11 12:00:00")
        ages = [pd.Timedelta(0), pd.Timedelta(days=30), pd.Timedelta(days=30, seconds=1),
                pd.Timedelta(seconds=-1), pd.NaT, pd.Timedelta(days=60)]
        tx = [dict(msisdn1=f"081000000{i}", created_at=instant) for i in range(6)]
        customers = [dict(msisdn1=f"24381000000{i}", created_at=instant - age) for i, age in enumerate(ages)]
        customers.append(dict(msisdn1="243810000005", created_at=instant))
        result = build_mpesa_recent_customer_activity_summary(prepared(tx, customers))
        self.assertEqual(result.iloc[0].valeur, "33.33 % (2 / 6)")
        self.assertEqual(result.iloc[1].valeur, 1)

    def test_first_transaction_of_filtered_period_and_direction(self):
        data = prepared([
            dict(msisdn1="0810000001", created_at="2026-08-01 09:00:00", sens_flux="Entree"),
            dict(msisdn1="0810000001", created_at="2026-09-11 09:00:00", sens_flux="Entree"),
            dict(msisdn1="0810000002", created_at="2026-09-11 09:00:00", sens_flux="Sortie"),
            dict(msisdn1="0810000003", created_at="2026-09-11 11:00:00", sens_flux="Entree"),
        ], [dict(msisdn1="0810000001", created_at="2026-09-01 00:00:00")])
        result = build_mpesa_recent_customer_activity_summary(
            data, date_start="2026-09-11 09:00:00", date_end="2026-09-11 10:00:00", directions=["Entree"],
        )
        self.assertEqual(result.iloc[0].valeur, "100.00 % (1 / 1)")

    def test_unavailable_is_not_zero(self):
        tx = [dict(msisdn1="0810000001", created_at="2026-09-11")]
        for data in (prepared([], []), prepared(tx, []), prepared(tx, [dict(msisdn1="0810000001", created_at="invalid")])):
            with self.subTest(data=data):
                self.assertEqual(build_mpesa_recent_customer_activity_summary(data).iloc[0].valeur, "Non calculable")
        data = prepared(tx, [dict(msisdn1="0810000001", created_at="2025-01-01")])
        self.assertEqual(build_mpesa_recent_customer_activity_summary(data).iloc[0].valeur, "0.00 % (0 / 1)")

    def assert_exports(self, data, start, end):
        metric = build_mpesa_recent_customer_activity_summary(data, date_start=start, date_end=end)
        summary = pd.concat([build_mpesa_customer_period_summary(data, date_start=start, date_end=end), metric], ignore_index=True)
        label, value = metric.iloc[0][["indicateur", "valeur"]]
        xlsx = create_excel_export({"clients_periode": summary})
        exported = pd.read_excel(BytesIO(xlsx), sheet_name="Synthese_Clients")
        self.assertEqual(exported.loc[exported.indicateur.eq(label), "valeur"].tolist(), [value])
        docx = create_g2_dat_word(
            {"clients_periode": summary, "analysis_source_label": "Solution Numérique",
             "analysis_date_start": start, "analysis_date_end": end},
            period_text=f"du {start} au {end}", direction_label="Tous", generated_at=end,
        )
        document = Document(BytesIO(docx))
        cells = [cell.text for table in document.tables for row in table.rows for cell in row.cells]
        self.assertEqual(cells.count(label), 1)
        self.assertIn(value, cells)

    def test_word_and_excel_export(self):
        data = prepared([dict(msisdn1="0810000001", created_at="2026-09-11")],
                        [dict(msisdn1="0810000001", created_at="2026-09-01")])
        self.assert_exports(data, pd.Timestamp("2026-09-01"), pd.Timestamp("2026-09-12"))

    @unittest.skipUnless(os.environ.get("MPESA_QA_INPUT_DIR"), "Classeurs locaux optionnels")
    def test_real_workbooks_read_only(self):
        import hashlib

        source = Path(os.environ["MPESA_QA_INPUT_DIR"])
        paths = sorted(source.glob("*.xlsx"))
        hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        def load(pattern):
            selected = [p for p in paths if pattern in p.name]
            self.assertTrue(selected, pattern)
            return pd.concat([pd.read_excel(p, engine="calamine") for p in selected], ignore_index=True)
        data = prepared(prepare_transactions(load("Transactions")), prepare_customers(load("Customers")))
        tx_dates = pd.to_datetime(data.transactions.created_at, errors="coerce")
        # Independent dictionary/set calculation, separate from the service's groupby/join.
        creation = {}
        for phone, instant in zip(normalize_phone(data.customers.msisdn1), pd.to_datetime(data.customers.created_at, errors="coerce")):
            if pd.notna(phone) and pd.notna(instant):
                creation[phone] = min(instant, creation.get(phone, instant))
        print(f"\nSources: {len(data.transactions)} transactions, {len(data.customers)} Customers; dates {tx_dates.min()} - {tx_dates.max()}")
        last_day = tx_dates.max().normalize()
        periods = [(tx_dates.min(), tx_dates.max()), (last_day, tx_dates.max()),
                   (last_day - pd.Timedelta(days=1), last_day - pd.Timedelta(seconds=1))]
        for start, end in periods:
            first = {}
            for phone, instant in zip(normalize_phone(data.transactions.msisdn1), tx_dates):
                if pd.notna(phone) and pd.notna(instant) and start <= instant <= end:
                    first[phone] = min(instant, first.get(phone, instant))
            numerator = sum(phone in creation and pd.Timedelta(0) <= instant - creation[phone] <= pd.Timedelta(days=30)
                            for phone, instant in first.items())
            missing = sum(phone not in creation for phone in first)
            result = build_mpesa_recent_customer_activity_summary(data, date_start=start, date_end=end)
            self.assertEqual(result.iloc[0].valeur, f"{100 * numerator / len(first):.2f} % ({numerator} / {len(first)})")
            self.assertEqual(result.iloc[1].valeur, missing)
            self.assert_exports(data, start, end)
            print(f"Periode {start} - {end}: {result.iloc[0].valeur}; creation manquante: {missing}; exports Word/Excel conformes")
        self.assertEqual(hashes, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
