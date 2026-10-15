"""Sélection exacte d'un seul batch. Ce module n'exécute jamais de SQL."""
import re

BEGIN = "-- BEGIN IMF_BB CBS SOURCE CONTRACTS"
END = "-- END IMF_BB CBS SOURCE CONTRACTS"
CODES = ("148_CBS", "162_CBS", "163_CBS", "164_CBS")


def select_query(text, code):
    code = str(code)
    if code in CODES:
        start, end = f"-- BEGIN CBS {code}\n", f"-- END CBS {code}"
        normalized = text.replace("\r\n", "\n")
        if normalized.count(start) != 1 or normalized.count(end) != 1:
            raise ValueError("Variante CBS absente ou ambiguë dans le catalogue.")
        result = normalized.split(start, 1)[1].split(end, 1)[0].strip()
        if not re.search(r"DECLARE\s+@executer\s+bit\s*=\s*0\s*;", result, re.I):
            raise ValueError("La garde de prévisualisation CBS doit rester à zéro.")
        if re.search(r"^\s*GO\b", result, re.I | re.M):
            raise ValueError("Une variante CBS doit rester un batch autonome.")
        return result + "\n"
    if not re.fullmatch(r"\d{1,3}[A-Z]?", code):
        raise ValueError("Sélecteur inconnu : utilisez par exemple 148 ou 148_CBS.")
    original = text.split(BEGIN, 1)[0]
    headers = list(re.finditer(r"(?m)^\s*(?:/\*\s*)?(\d{1,3}[A-Z]?)\.\s+[^\r\n]+", original))
    matches = [i for i, match in enumerate(headers) if match[1] == code]
    if len(matches) != 1:
        raise ValueError("Requête historique absente ou ambiguë.")
    index = matches[0]
    block = original[headers[index].start():headers[index + 1].start() if index + 1 < len(headers) else len(original)]
    if "*/" in block:
        block = block.split("*/", 1)[1]
    return block.removesuffix("/*").strip() + "\n"
