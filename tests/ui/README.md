# Tests d'interface (happy-dom)

Ces tests exécutent réellement l'interface (modules ES, rendu DOM, appels API)
contre un serveur Delivra en cours d'exécution. Ils vérifient :

- le chargement des 7 modules ES sans erreur ;
- le rendu de l'assistant et le passage brief → structure ;
- le rendu de l'éditeur, des 5 onglets et de l'aperçu A4 (image reçue) ;
- l'ajout d'un bloc de contenu ;
- les vues projets, médias/exports et paramètres.

## Lancer

```bash
# 1. serveur (dans un terminal)
python run.py --port 8080 --no-browser

# 2. tests (dans un autre terminal)
cd tests/ui
npm install happy-dom
node run.mjs            # parcours complet
node tabs.mjs           # onglets de l'éditeur
```

Les scripts convertissent les modules du dossier `delivra/static/js` en `.mjs`
temporaires (`mods/`) puis les importent nativement : ce que teste le harnais est
exactement le code servi par le navigateur.
