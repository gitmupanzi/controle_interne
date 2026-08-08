# Contrôle interne IMF

Application Streamlit de contrôle interne, d'analyse métier et de reporting pour la Microfinance Bisou Bisou S.A.

La documentation détaillée du projet est centralisée dans le site web MkDocs :

- Perfect Vision ;
- Perfect Power BI ;
- Solution Numérique ;
- règles transversales, devises, qualité, sécurité et changelog.

## Démarrage rapide

### Environnement Python

Sur l'ordinateur principal :

```powershell
$PYTHON = 'C:\Users\Benjamin-mupanzi\AppData\Local\anaconda3\python.exe'
```

Sur un autre ordinateur :

```powershell
$PYTHON = 'C:\ProgramData\anaconda3\python.exe'
```

### Installer les dépendances

```powershell
& $PYTHON -m pip install -r requirements.txt
```

### Lancer l'application Streamlit

```powershell
& $PYTHON -m streamlit run .\controle_interne.py
```

### Lancer les tests

```powershell
& $PYTHON -m unittest discover -s tests -v
```

## Documentation web

### Consulter en local sans serveur

```powershell
& $PYTHON -m mkdocs build
Start-Process .\site\index.html
```

### Consulter en direct pendant la rédaction

```powershell
& $PYTHON -m mkdocs serve
```

### Publier avec GitHub Pages

```powershell
& $PYTHON -m mkdocs gh-deploy
```

Lien prévu après publication :

```text
https://gitmupanzi.github.io/controle_interne/
```

## Structure principale

```text
controle_interne.py              Point d'entrée Streamlit
credit_app/                      Modules applicatifs et métiers
data/                            Référentiels, SQL, Power BI et modèles
documentation_web/               Documentation web centralisée
skills/                          Règles de travail Codex par domaine
tests/                           Tests automatisés
mkdocs.yml                       Configuration du site documentaire
requirements.txt                 Dépendances Python
```

## Règles importantes

- Les montants CDF et USD ne doivent pas être additionnés sans conversion officielle documentée.
- Les secrets, mots de passe et chaînes de connexion réelles ne doivent jamais être versionnés.
- Les données clients réelles ne doivent pas être publiées dans la documentation.
- Toute évolution métier ou technique doit mettre à jour la documentation web concernée.
