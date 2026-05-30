# CV Repo

Ce dépôt sert à gérer des candidatures LaTeX de manière structurée et semi-automatique.

## Structure

### Ressources communes à la racine

Ces fichiers restent à la racine car ils sont partagés :

- `altacv.cls`
- `pubs-num.tex`
- `pubs-authoryear.tex`
- `sample.bib`
- `moi.jpeg`
- `orcid.svg`
- `Globe_High.png`
- `Suitcase_High.png`
- `Yacht_High.png`
- `6892(1).pdf`

### Candidatures

Les candidatures sont rangées dans :

```text
applications/<entreprise>/<offre>/
```

Exemples :

- `applications/alten/ait-spatial/`
- `applications/thales/rams-safety/`
- `applications/viveris/ivvq/`

Toutes les candidatures partagent un seul dossier commun :

```text
applications/_shared/
```

Il contient les ressources communes utilisées par les `.tex`.
Les dossiers `applications/<entreprise>/<offre>/` ne gardent qu'un lien local `altacv.cls` pour permettre la compilation directe depuis le dossier.

### Templates

Les modèles non rattachés à une offre précise sont rangés dans :

```text
templates/cv/
templates/letters/
templates/research/
templates/misc/
templates/_shared/
```

## Objectif de l’automatisation

Quand un nouveau `.tex` est déposé à la racine du repo, le script doit :

1. détecter le fichier ;
2. deviner l’entreprise et l’offre à partir du nom ;
3. créer les dossiers manquants si nécessaire ;
4. déplacer le fichier au bon endroit ;
5. corriger automatiquement les chemins pour qu’il compile depuis son nouveau dossier ;
6. créer un fichier `.xmpdata` si nécessaire pour éviter le warning `pdfx` ;
7. compiler avec `latexmk` ;
8. relancer automatiquement si le warning `rerunfilecheck` demande une seconde passe ;
9. signaler les warnings restants et les placeholders non remplacés.

Si l’entreprise ou l’offre ne peuvent pas être déduites proprement, le fichier est rangé dans :

```text
applications/_unsorted/<slug-du-fichier>/
```

## Scripts

### Exécution ponctuelle

```bash
python3 scripts/auto_tex_manager.py
```

Cette commande traite tous les nouveaux `.tex` présents à la racine.

Avec commit automatique :

```bash
python3 scripts/auto_tex_manager.py --git-commit
```

Avec commit et push automatiques :

```bash
python3 scripts/auto_tex_manager.py --git-push
```

Avec message personnalisé conforme a Conventional Commits :

```bash
python3 scripts/auto_tex_manager.py --git-push --commit-message "feat(softeam): add ai application files"
```

### Mode surveillance

```bash
./scripts/auto_tex_watch.sh
```

Ce mode surveille la racine du repo et traite automatiquement tout nouveau `.tex`.

Si vous voulez aussi commit/push automatiquement en mode surveillance, lancez directement :

```bash
python3 scripts/auto_tex_manager.py --watch --git-push
```

## Ce que le script modifie automatiquement

Le script [scripts/auto_tex_manager.py](/home/gboileau/Documents/CV/Resume_guillaume_boileau_phd(2)/scripts/auto_tex_manager.py) applique notamment :

- normalisation de `\documentclass{altacv}` ;
- ajout ou correction des chemins vers :
  - `../../_shared/pubs-num.tex` pour les candidatures
  - `../../_shared/pubs-authoryear.tex` pour les candidatures
  - `../../_shared/sample.bib` pour les candidatures
  - `../../_shared/moi` pour les candidatures
  - `../_shared/...` pour les templates
- création d’un lien local `altacv.cls` dans le dossier cible ;
- création du `.xmpdata` pour les lettres ou documents `pdfx`.

## Warnings gérés automatiquement

Le script sait corriger ou absorber automatiquement certains cas fréquents :

- warning `pdfx` dû à l’absence de `.xmpdata`
- warning `rerunfilecheck` qui disparaît après recompilation
- mauvais chemin vers `altacv.cls` ou les ressources partagées

## Warnings non corrigés automatiquement

Le script peut encore vous signaler des cas qui dépendent du contenu métier :

- placeholders encore présents dans un template
- erreurs LaTeX propres au contenu du fichier
- structure de document incohérente ou incomplète

## Placeholders détectés

Le script signale certains placeholders typiques, par exemple :

- `[Nom du Poste]`
- `[Entreprise]`
- `[Année]`
- `[Lieu]`
- `[Responsabilité 1]`
- `Nom de l'Entreprise`
- `poste actuel`

## Convention de nommage recommandée

Pour aider le classement automatique, utilisez autant que possible des noms comme :

- `CV_Guillaume_Boileau_ALTEN_AIT_Spatial.tex`
- `LM_Guillaume_Boileau_ALTEN_AIT_Spatial.tex`
- `letter_Company_Offer.tex`

Plus le nom est explicite, meilleur sera le classement.

Format simple recommandé :

- `CV_Prenom_Nom_ENTREPRISE_OFFRE.tex`
- `LM_Prenom_Nom_ENTREPRISE_OFFRE.tex`
- `letter_Prenom_Nom_COMPANY_ROLE.tex`

Règles pratiques :

- utiliser `_` comme séparateur ;
- mettre le type de document au début : `CV`, `LM`, `letter`, `Lettre` ;
- mettre ensuite prénom et nom ;
- mettre ensuite l’entreprise ;
- terminer par l’offre ou l’intitulé du poste ;
- éviter les espaces, accents, parenthèses et caractères spéciaux dans le nom du fichier.

Exemples :

- `CV_Guillaume_Boileau_SOFTEAM_ingenieur_ia.tex`
- `LM_Guillaume_Boileau_THALES_rams_safety.tex`
- `CV_Guillaume_Boileau_GROUPAGORA_ingenieur_systeme_embarque.tex`

## Conventional Commits

Le script peut maintenant versionner automatiquement les changements avec un message au format :

```text
<type>[optional scope]: <description>
```

Exemples utilises dans ce repo :

- `feat(repo): automate tex organization and compilation`
- `feat(softeam): organize CV_Guillaume_boileau_SOFTEAM_ingenieur_ia.tex into applications/softeam/ingenieur-ia`

Reference :
- https://www.conventionalcommits.org/en/v1.0.0/

## Prompt simple pour GPT

Si vous voulez juste demander à GPT un nom de fichier correct, utilisez ce prompt :

```text
Donne-moi uniquement le nom du fichier `.tex`, sans explication.

Format obligatoire :
- pour un CV : `CV_Prenom_Nom_ENTREPRISE_OFFRE.tex`
- pour une lettre : `LM_Prenom_Nom_ENTREPRISE_OFFRE.tex`

Contraintes :
- séparateur `_` uniquement
- pas d’espace
- pas d’accent
- pas de parenthèses
- pas de caractères spéciaux
- entreprise et offre en majuscules/minuscules simples compatibles avec un nom de fichier

Informations :
- prénom : Guillaume
- nom : Boileau
- entreprise : [nom entreprise]
- offre : [nom offre]
- type : [CV ou LM]
```

## Exemple de workflow

1. Déposer un nouveau fichier `.tex` à la racine.
2. Lancer :

```bash
python3 scripts/auto_tex_manager.py
```

3. Lire le rapport terminal, par exemple :

```text
[move] LM_Foo_Bar.tex -> applications/foo/bar
       created: applications/foo/bar
       compile: ok
       fixes: created_xmpdata, rerun_for_outlines
```

4. Ouvrir ensuite le fichier depuis son nouveau dossier dans `applications/...`.

## Limites actuelles

- Le classement repose principalement sur le nom du fichier.
- Le script n’interprète pas le sens complet du contenu métier.
- Les anciens onglets VS Code peuvent pointer vers les anciens chemins tant qu’ils ne sont pas rouverts.

## Entretien du repo

Pour garder le repo propre :

- déposer les nouveaux `.tex` uniquement à la racine avant traitement ;
- laisser le watcher tourner si vous voulez un traitement automatique continu ;
- ouvrir les fichiers classés depuis `applications/...` ou `templates/...` après traitement ;
- éviter de modifier manuellement les liens `_shared` sauf nécessité.
