from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".toml", ".json", ".txt"}
MOJIBAKE_MARKERS = ("\u00c3", "\u00e2\u20ac\u2122", "\u00e2\u20ac\u0153", "\u00e2\u20ac", "\ufffd")
INTENTIONAL_MOJIBAKE_HANDLER = ROOT / "credit_app" / "colonne_valeur" / "colonne_nettoyage.py"


def _user_facing_text_files() -> list[Path]:
    candidates = [ROOT / "README.md", ROOT / "controle_interne.py"]
    for folder in (ROOT / "credit_app", ROOT / "skills"):
        candidates.extend(path for path in folder.rglob("*") if path.suffix.casefold() in TEXT_SUFFIXES)
    return sorted(set(candidates))


def test_user_facing_sources_are_valid_utf8_without_bom() -> None:
    failures: list[str] = []
    for path in _user_facing_text_files():
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            failures.append(f"{path.relative_to(ROOT)} contient un BOM UTF-8")
        try:
            raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            failures.append(f"{path.relative_to(ROOT)} n'est pas un UTF-8 valide : {exc}")
    assert not failures, "\n".join(failures)


def test_user_facing_sources_do_not_contain_mojibake() -> None:
    failures: list[str] = []
    for path in _user_facing_text_files():
        if path == INTENTIONAL_MOJIBAKE_HANDLER:
            continue
        text = path.read_text(encoding="utf-8")
        markers = [marker for marker in MOJIBAKE_MARKERS if marker in text]
        if markers:
            failures.append(f"{path.relative_to(ROOT)} contient : {', '.join(map(ascii, markers))}")
    assert not failures, "\n".join(failures)
