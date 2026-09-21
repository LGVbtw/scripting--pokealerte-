# stock-alert

Surveille disponibilité produit sur pages e-commerce publiques, alerte Discord sur passage indisponible -> disponible. Tourne gratuit dans GitHub Actions, cron 5 min, aucune dépendance PC perso.

Lecture HTML public seule, comme refresh manuel navigateur. Pas de bot d'achat, pas de bypass CAPTCHA/anti-bot.

## Fichiers

- `check_stock.py` — logique check + alerte
- `state.json` — état précédent par produit (committé auto par le workflow)
- `.github/workflows/check.yml` — cron GitHub Actions
- `requirements.txt` — deps Python

## 1. Créer webhook Discord

1. Ouvrir Discord (app ou web).
2. Aller sur serveur cible. **Recommandé : créer un serveur perso privé rien que pour toi** (bouton `+` en bas à gauche de la liste serveurs -> "Créer un serveur" -> "Pour moi et mes amis" ou juste toi). Évite bruit dans salon partagé, évite spam visible par d'autres.
3. Dans ce serveur, créer salon texte dédié, ex `#alertes-stock` (clic droit sur catégorie -> "Créer un salon").
4. Clic roue crantée à côté du salon (ou clic droit salon -> "Modifier le salon") -> onglet **Intégrations**.
5. Cliquer **Webhooks** -> **Nouveau Webhook**.
6. Nommer webhook (ex "Stock Bot"), vérifier salon cible correct.
7. Cliquer **Copier l'URL du webhook**. Ressemble à `https://discord.com/api/webhooks/123456789/abcDEF...`.
8. Cliquer **Enregistrer**.

URL webhook = clé secrète. Quiconque la possède peut poster dans ton salon. Ne jamais la coller dans le code, ni la partager.

## 2. Créer/configurer repo GitHub

### Compte GitHub
Si pas de compte : github.com -> "Sign up" -> email, mot de passe, pseudo, vérifier email.

### Nouveau repository
1. github.com -> icône `+` en haut à droite -> **New repository**.
2. Nom, ex `stock-alert`.
3. **Privé recommandé** : c'est ton outil perso, aucune raison de l'exposer. Public marche aussi (Actions gratuit pareil sur repos publics) mais privé évite que n'importe qui voie tes URLs surveillées / structure.
4. Ne pas cocher "Add README" si tu push fichiers existants (évite conflit) — ou coche et merge après, comme tu veux.
5. **Create repository**.

### Ajouter les fichiers

**Option A — interface web** :
1. Sur page repo vide, cliquer "uploading an existing file" (ou "Add file" -> "Upload files").
2. Glisser `check_stock.py`, `requirements.txt`, `state.json`, `README.md`.
3. Pour `.github/workflows/check.yml` : GitHub web permet de créer chemin avec sous-dossiers en tapant le chemin complet dans le champ nom de fichier lors de "Add file" -> "Create new file" : taper `.github/workflows/check.yml`, coller contenu.
4. Commit direct sur `main` (bouton "Commit changes").

**Option B — ligne de commande git** (depuis dossier `stock-alert` en local) :
```bash
git init
git add .
git commit -m "init: stock alert bot"
git branch -M main
git remote add origin https://github.com/<ton-user>/stock-alert.git
git push -u origin main
```
Remplace `<ton-user>` par ton pseudo GitHub. Si demande login, utiliser token (Settings -> Developer settings -> Personal access tokens) au lieu de mot de passe.

## 3. Configurer GitHub Secret

1. Sur page repo GitHub -> **Settings** (onglet en haut).
2. Menu gauche -> **Secrets and variables** -> **Actions**.
3. Onglet **Secrets** (pas Variables) -> **New repository secret**.
4. Name : `DISCORD_WEBHOOK_URL` (exact, sensible à la casse).
5. Secret : coller URL webhook copiée étape 1.
6. **Add secret**.

## 4. Activer / vérifier GitHub Actions

1. Onglet **Actions** en haut du repo.
2. Workflow "Check stock" doit apparaître dans liste gauche (GitHub le détecte auto via `.github/workflows/check.yml`). Si message "Actions désactivées", cliquer "I understand my workflows, go ahead and enable them" (repos forkés) — normalement pas nécessaire sur repo créé par toi.
3. Test manuel : cliquer workflow "Check stock" dans liste gauche -> bouton **Run workflow** (dropdown à droite) -> branche `main` -> **Run workflow**.
4. Rafraîchir page après ~10-20s, run apparaît avec icône jaune (en cours) puis verte (succès) ou rouge (échec).
5. Cliquer sur le run -> cliquer job `check` -> déplier étapes pour voir logs. Chercher ligne genre `[example-product] available=False (was=False)`.
6. Si rouge : ouvrir étape en échec, lire dernière ligne d'erreur. Cas fréquents :
   - `403`/`429` : site bloque requête, ajuster User-Agent ou espacer fréquence.
   - `KeyError`/`Timeout` : voir message exact, souvent site down ou URL invalide.
   - `Permission denied` sur push état : vérifier `permissions: contents: write` présent dans `check.yml` (déjà inclus).

## 5. Test de bout en bout (déclencher fausse alerte)

1. Modifier `check_stock.py`, dans `PRODUCTS`, changer un mot-clé pour un mot forcément présent sur ta page test, ex mettre `"keywords": ["<html"]` temporairement (présent dans quasi toute page HTML).
2. Commit + push ce changement (ou édition directe fichier sur GitHub web + commit).
3. Lancer **Run workflow** manuellement (étape 4.3).
4. Vérifier salon Discord : message doit arriver avec nom produit, URL, heure UTC.
5. Une fois confirmé, **remettre mot-clé réel** (`"Ajouter au panier"` etc.), commit + push à nouveau.
6. Optionnel : remettre `state.json` à `{}` si tu veux re-tester transition indisponible->disponible proprement (sinon script ne realertera pas tant que état reste "available": true).

## 6. Ajouter une URL à surveiller

Éditer `check_stock.py`, dict `PRODUCTS`, ajouter entrée :
```python
"nouvelle-cle": {
    "name": "Nom Produit",
    "url": "https://site.com/produit",
    "keywords": ["En stock", "Ajouter au panier"],
},
```
Commit + push. Prochain run cron (ou manuel) prend en compte automatiquement.

## 7. Fréquence

Cron actuel `*/5 * * * *` = toutes les 5 min. Ne pas descendre en dessous (risque blocage anti-bot + limite GitHub Actions cron réel ~ 5 min mini garanti, souvent plus lent selon charge GitHub). Pour espacer, éditer `.github/workflows/check.yml` :
- 10 min : `*/10 * * * *`
- 30 min : `*/30 * * * *`
- horaire : `0 * * * *`

## 8. Workflow mis en pause (inactivité)

GitHub désactive auto les workflows cron après **60 jours sans activité repo** (repos publics et privés concernés). Signe : onglet Actions affiche bandeau "This scheduled workflow has been disabled because there hasn't been activity in this repository for at least 60 days".

Réactiver :
1. Onglet **Actions**.
2. Sélectionner workflow "Check stock" dans liste gauche.
3. Bandeau jaune en haut -> cliquer **Enable workflow**.

Pour éviter récidive : tout push (même petit commit) remet compteur à zéro. Alternative : ignorer, réactiver manuellement quand besoin reprend.

## Gestion erreurs déjà en place

- Timeout requête (15s) : catch `requests.RequestException`, log erreur, passe produit suivant sans crash.
- Site down / 4xx / 5xx : `raise_for_status()` capturé, log, run continue.
- Échec envoi Discord : catch séparé, état pas marqué "alerté" donc retry au run suivant.
- Mot-clé absent (site a changé structure) : simplement traité comme "indisponible", pas de crash.
