# Delivra — l'agent IA de vos documents livrables

**Delivra** transforme une description de projet en **dossier de livraison professionnel** :
couverture personnalisée, résumé exécutif, sommaire paginé, architecture, déploiement,
sécurité, recette, planning et risques — exporté en **PDF**, **Word** et **PowerPoint**.

Interface web locale + application de bureau autonome (`.exe` sous Windows).
**Aucune donnée ne quitte votre poste** : le moteur de génération est intégré.

---

## Sommaire

- [Aperçu](#aperçu)
- [Fonctionnalités](#fonctionnalités)
- [Démarrage rapide](#démarrage-rapide)
- [Applications exécutables (.exe)](#applications-exécutables-exe)
- [Utiliser l'agent](#utiliser-lagent)
- [Contenu d'un livrable](#contenu-dun-livrable)
- [Personnalisation (marque, polices, palettes)](#personnalisation-marque-polices-palettes)
- [Brancher un modèle de langage](#brancher-un-modèle-de-langage)
- [Architecture technique](#architecture-technique)
- [API REST](#api-rest)
- [Tests](#tests)
- [Dépannage](#dépannage)
- [Limites connues](#limites-connues)
- [Structure du projet](#structure-du-projet)
- [Licence](#licence)

---

## Aperçu

| Étape | Ce que fait Delivra |
|---|---|
| 1. Brief | Vous décrivez le client, la solution, le contexte, les objectifs et la stack. |
| 2. Structure | L'agent détecte le type de projet (cloud, data, web, intégration, sécurité, ERP) et propose un plan. |
| 3. Identité | Import des logos, choix de la palette, de la typographie et de la mise en page. |
| 4. Génération | Composition du document complet (10 sections, tableaux, KPI, schéma d'architecture). |
| 5. Édition | Ajustement fin dans l'éditeur avec **aperçu A4 en direct**. |
| 6. Export | PDF signable, Word éditable, PowerPoint de restitution, Markdown, pack ZIP. |

## Fonctionnalités

### Contenu du livrable
- **Couverture** générée (3 styles : pleine couleur, dégradé, minimaliste) avec logo client,
  badge de confidentialité, référence, version et tags de la stack.
- **Résumé exécutif** + bandeau « informations clés » + points à retenir.
- **Sommaire paginé automatiquement** (pagination réelle, calculée en deux passes).
- **Sections numérotées** avec en-tête, filets, filigrane et pied de page.
- **16 types de blocs** : titres, paragraphes, listes (1 ou 2 colonnes), encadrés,
  tableaux, chiffres clés, plannings, captures d'écran, schémas d'architecture,
  checklists, citations, blocs de code, signatures, colonnes comparatives…
- **Page de validation** avec blocs de signature.
- **Fiche de contrôle qualité** en annexe (score de complétude 0-100).

### Génération automatique
- **Moteur local** : 6 référentiels métier (cloud, data, web, intégration, sécurité, ERP),
  rédaction contextuelle des 10 sections, tableaux, risques, planning et KPIs.
- **Schéma d'architecture** généré en image PNG haute définition à partir de vos couches
  (*text to image*), également rendu en vectoriel dans le PDF.
- **Visuels de couverture** générés à partir de votre palette.
- **Reformulation** de paragraphes (moteur local, ou LLM si configuré).
- **Fournisseur LLM optionnel** : OpenAI, Mistral, Ollama local, Anthropic, endpoint
  compatible OpenAI. Dégradation automatique vers le moteur local en cas d'échec.

### Interface
- Assistant en 4 étapes (brief → structure → identité → génération).
- Éditeur complet : plan réordonnable, blocs modulaires, import par glisser-déposer.
- **Aperçu A4 fidèle** (rendu PDF → image), navigation page par page.
- Score de qualité en temps réel avec recommandations.
- Médiathèque (captures, logos), historique des exports, duplication de projets.
- Thème clair/sombre, sauvegarde automatique, stockage local JSON.

### Exports
| Format | Usage |
|---|---|
| **PDF** | Document final, prêt à signer, polices embarquées |
| **DOCX** | Réédition complète dans Word (styles, tableaux, images) |
| **PPTX** | Support de réunion : couverture, sections, KPI, tableaux, schémas |
| **Markdown** | Publication interne, wiki, Git |
| **ZIP** | Pack complet (PDF + DOCX + PPTX + JSON source) |

## Démarrage rapide

Prérequis : **Python 3.10+**.

```bash
git clone <votre-dépôt> Delivra && cd Delivra
python -m venv .venv
# Windows : .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt

python run.py            # ouvre http://127.0.0.1:8760
```

Options utiles :

```bash
python run.py --port 9000 --no-browser   # choisir le port, ne pas ouvrir le navigateur
python run.py --host 0.0.0.0             # accessible depuis le réseau local
python run.py --desktop                  # fenêtre native (nécessite pywebview)
```

Les documents sont stockés dans :
- Windows : `%APPDATA%\Delivra`
- macOS : `~/Library/Application Support/Delivra`
- Linux : `~/.local/share/Delivra`

Un dossier `data/` à la racine de l'application est utilisé s'il existe (mode portable,
pratique sur clé USB). Personnalisable via `DELIVRA_HOME`.

## Applications exécutables (.exe)

L'application se compile en exécutable autonome : **aucun Python à installer** sur le poste cible.

### Construire soi-même

```bash
pip install -r requirements-build.txt
python packaging/make_icon.py          # icône .ico / .png
python -m delivra.build --zip          # PyInstaller + archive
```

Résultat :
- **Windows** : `dist/Delivra/Delivra.exe` — double-clic, la fenêtre s'ouvre
  (WebView2, présent sur Windows 10/11 ; à défaut, le navigateur est utilisé).
- **Linux** : `dist/Delivra/Delivra`
- **macOS** : `dist/Delivra/Delivra` (dossier `.app` possible avec py2app)

### Télécharger un exécutable déjà compilé

Les binaires officiels sont attachés à chaque release :

> **[⬇ Delivra v1.0.0](https://github.com/Aboubeker/Free/releases/tag/v1.0.0)**

| Plateforme | Fichier | Utilisation |
|---|---|---|
| Windows 10/11 x64 | `Delivra-windows-x64.zip` | décompresser, double-cliquer **Delivra.exe** |
| Linux x64 | `Delivra-linux-x64.tar.gz` | `tar xzf … && ./Delivra/Delivra` |
| macOS (Apple Silicon) | `Delivra-macos-arm64.zip` | décompresser, lancer `Delivra` |

Aucune installation de Python n'est requise : l'exécutable embarque l'interpréteur,
les polices et toute l'interface. Les données (projets, médias, exports) sont
écrites dans un dossier utilisateur (`%APPDATA%\Delivra` sous Windows).

### Construction automatisée (GitHub Actions)

Le workflow [`.github/workflows/build.yml`](.github/workflows/build.yml) compile les trois
plateformes, **vérifie que le binaire démarre réellement** (`/healthz` + `/api/bootstrap`),
puis publie les archives en artefacts et les attache à une *release* lors d'un tag `v*`.
Le workflow [`.github/workflows/test.yml`](.github/workflows/test.yml) exécute la suite
de tests à chaque envoi.

```bash
git tag v1.0.0 && git push origin v1.0.0
```

État vérifié le 24/11/2026 : build **Windows, Linux et macOS en succès**, release
`v1.0.0` publiée avec les trois archives.

> **GitHub Actions doit être activé sur le dépôt** (*Settings → Actions → General →
> Allow all actions*). Si l'onglet *Actions* reste vide, aucun exécutable n'est
> produit ; le build local sous Windows (`python -m delivra.build --zip`) reste alors
> la référence.

> Le binaire Windows doit être produit sur Windows (ou via la CI) : PyInstaller ne
> réalise pas de compilation croisée.

## Utiliser l'agent

1. **Nouveau livrable** → renseignez au minimum un titre, le client et la solution.
   Le contexte et les objectifs améliorent sensiblement la rédaction.
2. Laissez la détection automatique ou choisissez le type de livrable, puis **Continuer**.
3. Réordonnez les sections par glisser-déposer ; ajoutez-en si besoin.
4. Choisissez la palette et la typographie, importez vos logos, cliquez **Générer le livrable**.
5. Dans l'éditeur, ajustez le contenu bloc par bloc — l'aperçu se met à jour.
6. Onglet **Qualité** : vérifiez le score, puis exportez en PDF / Word / PowerPoint.

Raccourcis : `Ctrl/⌘ + S` enregistre le document.

## Contenu d'un livrable

Les sections générées s'adaptent au type de projet :

| Section | Contenu généré |
|---|---|
| Contexte & enjeux | Situation actuelle, irritants, enjeux, objectif du document |
| Objectifs | Matrice objectifs/critères d'acceptation, KPI de succès |
| Périmètre | Inclus / exclus, dépendances, conditions |
| Architecture | Schéma en couches, choix techniques, principes de conception |
| Déploiement | Étapes de mise en production, pipeline, fenêtre de bascule |
| Intégrations | Inventaire des interfaces, règles d'échange |
| Sécurité | Checklists de conformité, mesures, réserves, signatures |
| Données | Jeux de données, règles de migration, contrôles qualité |
| Tests & recette | Stratégie, campagne, critères de réception |
| Exploitation | Engagements de service, supervision, jalons d'hypercare |
| Planning | Jalons contractuels, frise chronologique, gouvernance |
| Budget | Répartition par lot, charges, hypothèses |
| Risques | Registre, criticité, plan de mitigation |
| Résultats | Bénéfices mesurés, témoignages |
| Annexes | Documents associés, glossaire |

## Personnalisation (marque, polices, palettes)

### Polices embarquées

Quatre familles libres (SIL Open Font License) sont incluses et disponibles pour l'UI
comme pour le PDF, le DOCX et le PPTX :

| Famille | Usage recommandé |
|---|---|
| **Manrope** | Titres modernes, interface |
| **Sora** | Style technologique |
| **Source Serif 4** | Style éditorial / institutionnel |
| **JetBrains Mono** | Blocs de code, références |

Pour ajouter une police : déposez les fichiers `MaFonte-400.ttf`, `MaFonte-700.ttf` dans
`delivra/assets/fonts/`, ajoutez-la dans `WEIGHTS` et `FONT_STACKS` (`delivra/theme.py`),
puis régénérez l'exécutable.

Récupération automatique des polices de base :
```bash
python tools/fetch_fonts.py
```

### Palettes

Six palettes prêtes à l'emploi (`theme.PALETTES`) : Océan, Nuit, Émeraude, Graphite,
Sable, Bordeaux. Chaque palette définit couleur primaire, accent, encre, fonds et filets.
Les couleurs restent surchargeables projet par projet (onglet **Identité**).

### Mise en page

- Format : **A4** ou **US Letter**
- Densité : compacte, équilibrée, aérée
- Couverture : pleine couleur, dégradé ou minimaliste
- Filigrane, en-tête, pied de page, numérotation, sommaire, page de validation

## Brancher un modèle de langage

Le moteur local suffit pour produire un dossier complet. Un LLM améliore la rédaction
des paragraphes (structure et données restent gérées par Delivra).

**Interface** → *Paramètres* → fournisseur, clé, modèle, URL. Le bouton **Tester la
connexion** valide la configuration ; en cas d'échec, Delivra revient au moteur local.

**Variables d'environnement** (prioritaires) :

```bash
export DELIVRA_LLM_PROVIDER=openai       # openai | mistral | anthropic | ollama | custom
export DELIVRA_LLM_KEY=sk-...
export DELIVRA_LLM_MODEL=gpt-4o-mini
export DELIVRA_LLM_URL=http://localhost:11434/v1   # Ollama
```

Aucune clé n'est nécessaire en mode local, et aucun appel réseau n'est effectué si le
fournisseur reste sur `local`.

## Architecture technique

```
Navigateur (SPA sans dépendance)
   │  fetch JSON
   ▼
Flask (delivra/server.py) ──► Moteur IA (delivra/ai/engine.py)
   │                               ├─ référentiels métier (6 playbooks)
   │                               └─ fournisseur LLM optionnel
   ├──► Rendu PDF (delivra/render.py + pdfkit.py, ReportLab)
   ├──► Exports (delivra/export/*.py : docx, pptx, markdown)
   ├──► Diagrammes (delivra/diagrams.py, Pillow : architecture, visuels)
   └──► Stockage (delivra/storage.py : projets JSON, médias, exports)
```

- **Aucun CDN, aucune dépendance front** : l'interface est du HTML/CSS/JS natif en modules.
- **Aperçu fidèle** : le PDF est rendu puis converti en image (`pypdfium2`).
- **Pagination exacte** : le document est composé deux fois, le sommaire reçoit les
  numéros réels mesurés à la première passe.
- **Sécurité** : assainissement des entrées, formats d'upload limités, taille plafonnée,
  noms de fichiers normalisés, pas d'exécution de contenu utilisateur.

## API REST

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/bootstrap` | Catalogue (palettes, typographies, playbooks), état IA |
| POST | `/api/generate` | Génère un livrable complet depuis un brief |
| POST | `/api/plan` | Propose la structure (sections + pool) |
| POST | `/api/rewrite` | Reformule un texte |
| POST | `/api/suggest-titles` | Propose des titres |
| GET/POST | `/api/projects` | Liste / crée un livrable |
| GET/PUT/DELETE | `/api/projects/<id>` | Lire / enregistrer / supprimer |
| POST | `/api/projects/<id>/duplicate` | Dupliquer |
| POST | `/api/preview` | Rendu image des pages (`document` ou `id`, `pages`, `scale`) |
| POST | `/api/export/{pdf\|docx\|pptx\|md}` | Export binaire (`document`, `id` ou `brief`) |
| POST | `/api/export/preview-bundle` | ZIP multi-formats |
| POST | `/api/upload` | Import d'image (logo, capture) |
| GET/DELETE | `/api/assets[/<name>]` | Médiathèque |
| POST | `/api/visual` | Génération d'image (couverture, motif, architecture) |
| POST | `/api/ai/architecture` | Propose un schéma à partir d'une description |
| GET/POST | `/api/settings` | Configuration du fournisseur LLM |
| POST | `/api/quality` | Score de complétude d'un document |

Exemple :

```bash
curl -X POST http://127.0.0.1:8760/api/generate \
  -H "Content-Type: application/json" \
  -d '{"brief":{"title":"Dossier de livraison — Portail Client",
                 "client":"Banque Atlas","project":"Portail Client Omnicanal",
                 "industry":"Services financiers","weeks":20,
                 "stack":"React, API REST, PostgreSQL, Azure"},
        "save":true}'
```

## Tests

### Tests fonctionnels (35)

```bash
python -m unittest discover -s tests -v
```

Ils couvrent : normalisation et sécurité des entrées, détection du type de projet,
génération sur les 6 référentiels, contextualisation des indicateurs (par secteur,
reproductible), rendu PDF (toutes palettes / typographies / formats / variantes de
couverture / pagination du sommaire), exports DOCX/PPTX/Markdown, stockage, médias
(data-URI, validation) et l'ensemble des routes HTTP.

### Tests d'interface (happy-dom)

Ils exécutent réellement les modules ES de l'interface contre un serveur lancé :
rendu de l'assistant, passage brief → structure, éditeur et ses 5 onglets, aperçu A4,
ajout de blocs, vues projets / médias / paramètres, et contrôle d'absence d'erreur JS.

```bash
python run.py --port 8080 --no-browser &      # serveur
cd tests/ui && npm install happy-dom
node run.mjs && node tabs.mjs
```

Voir [`tests/ui/README.md`](tests/ui/README.md).

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `Le serveur Delivra ne répond pas` | port occupé / serveur arrêté | relancer `python run.py --port 8761` |
| Aperçu vide dans l'éditeur | `pypdfium2` absent | `pip install pypdfium2` |
| Aperçu qui échoue sur un document lourd | rendu partiel | l'erreur est affichée, le document reste éditable et exportable |
| Fenêtre native absente sous Windows | WebView2 manquant | Delivra bascule automatiquement sur le navigateur |
| Police introuvable dans le PDF | fichier `.ttf` renommé | conserver le format `Famille-Poids.ttf` (ex. `Manrope-700.ttf`) |
| `libpython3.11.so not found` au build | build PyInstaller sans bibliothèque partagée | compiler sous Windows (ou via la CI) |
| Export Word sans sommaire | Word n'évalue pas les champs à l'ouverture | clic droit sur le sommaire → « Mettre à jour les champs » |

## Limites connues

- La génération du contenu utilise un **moteur de règles** : le texte est structuré,
  précis et contextualisé, mais ne remplace pas une relecture métier. Brancher un LLM
  améliore la formulation.
- Les chiffres proposés à défaut de saisie sont **des cibles plausibles**, pas des
  mesures : remplacez-les par vos valeurs réelles avant diffusion.
- Le binaire doit être produit sur son système cible (pas de compilation croisée).
- Le PPTX est une déclinaison synthétique du dossier (couverture, sections, KPI,
  tableaux, schémas), non un jeu de slides rédigé sur mesure.

## Structure du projet

```
Delivra/
├── delivra/
│   ├── ai/engine.py          # moteur de génération (playbooks + LLM optionnel)
│   ├── export/               # DOCX, PPTX, Markdown
│   ├── static/               # interface web (HTML/CSS/JS, sans dépendance)
│   ├── assets/fonts/         # polices OFL + licences
│   ├── theme.py              # palettes, typographies, design system
│   ├── model.py              # schéma du livrable, validation, score qualité
│   ├── render.py             # rendu PDF (couverture, sections, blocs)
│   ├── pdfkit.py             # primitives de dessin ReportLab
│   ├── diagrams.py           # schémas et visuels (Pillow, text to image)
│   ├── storage.py            # persistance locale
│   ├── server.py             # API Flask + serveur
│   ├── desktop.py            # point d'entrée de l'application empaquetée
│   └── build.py              # script de construction PyInstaller
├── packaging/                # icônes et outils
├── tests/                    # tests fonctionnels (unittest) + interface (happy-dom)
├── tools/                    # polices, exemples, vérifications
├── delivra.spec              # configuration PyInstaller
├── .github/workflows/        # CI : builds Windows / Linux / macOS
└── run.py                    # lanceur de développement
```

## Licence

Code sous licence **MIT** (voir `LICENSE`).
Les polices embarquées sont distribuées sous **SIL Open Font License 1.1**
(fichiers `OFL-*.txt` dans `delivra/assets/fonts/`).
