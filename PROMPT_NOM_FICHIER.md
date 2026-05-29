# Prompt Nom De Fichier

Utilisez ce prompt pour demander a GPT uniquement un nom de fichier `.tex` compatible avec le repo.

```text
Donne-moi uniquement le nom du fichier `.tex`, sans explication.

Format obligatoire :
- pour un CV : `CV_Prenom_Nom_ENTREPRISE_OFFRE.tex`
- pour une lettre : `LM_Prenom_Nom_ENTREPRISE_OFFRE.tex`

Contraintes :
- separateur `_` uniquement
- pas d'espace
- pas d'accent
- pas de parentheses
- pas de caracteres speciaux

Informations :
- prenom : Guillaume
- nom : Boileau
- entreprise : [nom entreprise]
- offre : [nom offre]
- type : [CV ou LM]
```

Exemples attendus :

- `CV_Guillaume_Boileau_SOFTEAM_ingenieur_ia.tex`
- `LM_Guillaume_Boileau_THALES_rams_safety.tex`
- `CV_Guillaume_Boileau_GROUPAGORA_ingenieur_systeme_embarque.tex`
