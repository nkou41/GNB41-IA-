import os
import json
import re
import time
import requests
import anthropic
import openai


def _with_retry(func, max_attempts=4):
    """Reessaie une fois en cas de timeout/erreur reseau avant d'abandonner."""
    def wrapper(*args, **kwargs):
        last_result = None
        for attempt in range(max_attempts):
            last_result = func(*args, **kwargs)
            if last_result.get('statut') != 'erreur':
                return last_result
            msg = str(last_result.get('message', ''))
            is_retryable = 'timed out' in msg.lower() or 'timeout' in msg.lower() or 'connection' in msg.lower()
            if not is_retryable or attempt == max_attempts - 1:
                return last_result
            time.sleep(2)
        return last_result
    return wrapper

SYSTEM_PROMPT = """Tu es un ingénieur logiciel senior qui génère des applications complètes, professionnelles et prêtes à déployer, dans le style d'outils comme Base44 ou Bolt.new.

Règles strictes :
1. SAUF demande explicite d'une autre stack (React, Vue, backend Node/Flask...), utilise du HTML/CSS/JS pur en plusieurs pages/fichiers .html distincts relies par des liens <a href="...">. Cette stack est deployee automatiquement et instantanement par la plateforme sans etape de compilation — React et les frameworks necessitant un build (npm run build) ne peuvent PAS etre deployes automatiquement pour le moment, donc evite-les sauf si l'utilisateur les demande explicitement par leur nom.
2. Genere un ENSEMBLE COMPLET d'ecrans professionnels correspondant au type d'application demandee, pas un ecran minimal isole. Par exemple pour une application bancaire : page de connexion/inscription, tableau de bord avec solde et resume, liste des transactions, page de virement, page de parametres du compte. Pour un site e-commerce : accueil/catalogue, fiche produit, panier, paiement, compte client. Adapte la liste des ecrans au domaine metier precis de la demande.
3. Le code doit être complet, fonctionnel, sans placeholder ni "TODO". Chaque fichier doit pouvoir être utilisé tel quel. Aucun texte de remplissage generique (type "Lorem ipsum", "Common Marketing", "Sample Text") : tout le texte doit etre du vrai contenu pertinent pour l'application demandee, en francais sauf demande contraire. Comme aucune image ne peut etre generee ou telechargee, ne jamais utiliser de balise <img> pointant vers un fichier inexistant ou un service de placeholder externe (via.placeholder.com, picsum, etc.) : remplace toute illustration par un element visuel en CSS pur (degrade de couleur, forme geometrique, icone SVG inline ou emoji) qui s'integre proprement au design.
4. Structure le projet en plusieurs fichiers propres (pas un seul fichier monolithique), avec une organisation claire (dossiers si nécessaire).
5. Applique les bonnes pratiques : gestion d'erreurs, validation des entrées, sécurité de base, code lisible et commenté quand utile.
5b. Design visuel professionnel obligatoire, au niveau d'une vraie application mobile/web moderne (pas du HTML brut sans style) :
   - UN SEUL fichier style.css partage, reference de maniere identique par TOUTES les pages HTML avec exactement <link rel="stylesheet" href="style.css">. Verifie que chaque fichier .html genere contient bien cette ligne dans son <head>, sans exception.
   - Systeme de couleurs coherent (2-3 couleurs principales + une couleur d'accent), meme typographie sur tout le site, coins arrondis, ombres douces, espacements genereux et reguliers (comme Material Design ou les interfaces iOS/Android natives).
   - Composants visuels soignes : cartes avec ombre legere pour regrouper l'information, icones (utilise des caracteres unicode/emoji simples ou des SVG inline, jamais de dependance externe), grille responsive, boutons avec etats hover/actif clairement visibles.
   - Navigation claire et persistante (barre de navigation ou menu identique sur toutes les pages), pas juste une liste de liens texte brut.
   - Si un fichier JS est partage entre plusieurs pages (script.js), verifie de la meme maniere qu'il est reference de facon identique partout ou necessaire.
6. Inclus un fichier README.md expliquant comment installer et lancer le projet.
6b. Robustesse technique exigee sur CHAQUE formulaire et action utilisateur :
   - Validation cote client de tous les champs de saisie avant soumission (champs vides, format email, longueur minimale de mot de passe, etc.) avec messages d'erreur clairs affiches pres du champ concerne.
   - Gestion des cas limites : liste vide (afficher un message "Aucun element" plutot qu'un espace vide), action en cours (indicateur de chargement sur les boutons), succes d'une action (confirmation visuelle claire, pas juste un silence).
   - Aucune fonction JavaScript ne doit planter si une donnee est absente ou mal formee : verifie toujours l'existence d'une donnee avant de l'utiliser.
6c. Interactivite JavaScript reelle et non decorative, adaptee au type d'application :
   - Les listes affichees (produits, taches, messages, transactions...) doivent etre generees dynamiquement en JavaScript a partir de donnees (tableau JS local si pas de table declaree, ou API si table declaree), pas codees en dur ligne par ligne dans le HTML.
   - Les actions annoncees doivent reellement fonctionner : un bouton "Ajouter" ajoute vraiment un element visible immediatement, un bouton "Supprimer" retire vraiment l'element, un filtre/une recherche filtre vraiment l'affichage en temps reel.
   - Utilise des transitions CSS legeres (transition, transform) sur les interactions (survol, clic, apparition d'element) pour une sensation fluide et moderne, sans exagerer.

7. Si l'application a besoin de stocker des données persistantes (utilisateurs, produits, messages, taches, etc.), NE CODE PAS de backend/base de donnees toi-meme pour ca. Declare plutot les tables necessaires dans le champ "tables" (voir format ci-dessous), et utilise dans ton code JS l'API REST déjà fournie par la plateforme :
   - Base URL: {{API_BASE}}
   - Cle a envoyer dans le header "X-API-Key: {{API_KEY}}" sur CHAQUE requete vers cette API
   - Lister les lignes: GET {{API_BASE}}/appdb/v1/tables/{{TABLE_ID:nom_table}}/rows
   - Creer une ligne: POST {{API_BASE}}/appdb/v1/tables/{{TABLE_ID:nom_table}}/rows avec un JSON correspondant aux colonnes
   - Modifier une ligne: PUT {{API_BASE}}/appdb/v1/tables/{{TABLE_ID:nom_table}}/rows/<id_ligne>
   - Supprimer une ligne: DELETE {{API_BASE}}/appdb/v1/tables/{{TABLE_ID:nom_table}}/rows/<id_ligne>
   Remplace nom_table par le nom exact de la table declaree. Ces placeholders {{API_BASE}}, {{API_KEY}} et {{TABLE_ID:nom_table}} seront automatiquement remplaces par les vraies valeurs apres generation — utilise-les tels quels dans le code JS genere, ne les invente pas differemment.

Avant de generer, analyse la demande et decompose-la en etapes si elle est complexe (plusieurs fonctionnalites ou fichiers concernes). Pour une demande simple, le plan peut contenir une seule etape.

VERIFICATION FINALE OBLIGATOIRE avant de repondre : relis la liste complete des "fichiers" que tu vas inclure, puis pour CHAQUE fichier .html verifie un par un que : (1) il contient bien <link rel="stylesheet" href="style.css"> si un style.css existe dans ta liste, (2) chaque lien href= ou src= qu'il contient correspond exactement au chemin d'un autre fichier present dans ta liste "fichiers" (aucun lien mort), (3) aucun texte de remplissage generique n'y figure. Si tu detectes un probleme en te relisant, corrige-le avant de repondre plutot que d'envoyer un fichier incomplet.

Reponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après, au format exact suivant :
{
  "comprehension": "Une phrase courte reformulant ce que tu as compris de la demande, et si applicable, quels fichiers existants sont modifies",
  "plan": ["Etape courte 1", "Etape courte 2"],
  "decisions_a_retenir": ["Uniquement si une convention/contrainte technique durable doit etre memorisee pour les prochaines generations, sinon liste vide"],
  "description": "Description courte de l'application générée",
  "stack": "Nom de la stack technique utilisée",
  "tables": [
    {"nom": "taches", "colonnes": [{"nom": "titre", "type": "texte", "requis": true}, {"nom": "fait", "type": "booleen", "requis": false}]}
  ],
  "fichiers": [
    {"chemin": "index.html", "contenu": "..."},
    {"chemin": "style.css", "contenu": "..."}
  ]
}

Le champ "tables" est optionnel (liste vide si l'app n'a pas besoin de stockage persistant). Types de colonnes valides: "texte", "nombre", "booleen", "date".

Si la demande est ambigue au point de bloquer une generation fiable (ex: information essentielle manquante, choix technique non precise qui changerait completement le resultat), ne genere PAS de code au hasard. Renvoie plutot un JSON avec "fichiers": [] et "comprehension" commencant EXACTEMENT par "CLARIFICATION_NECESSAIRE: " suivi de ta question precise. N'utilise ce mecanisme que si c'est reellement bloquant, pas pour des details mineurs que tu peux raisonnablement deduire.
"""


def _verifier_fichiers(fichiers, fichiers_connus=None):
    """Controles basiques post-generation: placeholders oublies, fichiers vides, references cassees.
    fichiers_connus: chemins deja presents dans le projet avant cette generation (evite les faux positifs
    quand un fichier existant n'est pas retourne dans cette reponse car non modifie)."""
    avertissements = []
    noms_fichiers = set(f.get('chemin', '') for f in fichiers)
    if fichiers_connus:
        noms_fichiers = noms_fichiers | set(fichiers_connus)
    q = chr(34) + chr(39)

    for f in fichiers:
        chemin = f.get('chemin', '?')
        contenu = f.get('contenu', '') or ''

        if not contenu.strip():
            avertissements.append('Fichier vide: ' + chemin)
            continue

        if 'TODO' in contenu or 'PLACEHOLDER' in contenu.upper():
            avertissements.append('Placeholder non resolu detecte dans ' + chemin)

        if chemin.endswith('.html'):
            pattern = '(?:href|src)=[' + q + '](?!http|#|mailto:|data:|\\{\\{)([^' + q + '\\s]+)[' + q + ']'
            refs = re.findall(pattern, contenu)
            for ref in refs:
                if ref not in noms_fichiers:
                    avertissements.append(chemin + ' reference ' + ref + ' qui n\'est pas parmi les fichiers generes')

        motifs_secrets = [
            'sk-ant-[A-Za-z0-9_-]{10,}',
            'sk-[A-Za-z0-9]{20,}',
            'AIza[A-Za-z0-9_-]{20,}',
            '(?:api[_-]?key|apikey|secret[_-]?key)\\s*[:=]\\s*[' + q + '][A-Za-z0-9_-]{12,}[' + q + ']',
            'password\\s*[:=]\\s*[' + q + '](?!\\{\\{)[^' + q + ']{4,}[' + q + ']',
        ]
        for motif in motifs_secrets:
            if re.search(motif, contenu, re.IGNORECASE):
                avertissements.append('Possible secret code en dur detecte dans ' + chemin + ' - a verifier manuellement')
                break

    return avertissements


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(json)?\n', '', text)
        text = re.sub(r'\n```$', '', text)
    return text


def _repair_truncated_json(text: str):
    """Tente de recuperer un JSON tronque en coupant au dernier fichier complet."""
    matches = list(re.finditer(r'"\s*\}\s*,\s*(?=\{)', text))
    if not matches:
        return None
    last = matches[-1]
    cut = text[:last.end()]
    cut = re.sub(r',\s*$', '', cut)
    repaired = cut + '\n  ]\n}'
    try:
        json.loads(repaired)
        return repaired
    except json.JSONDecodeError:
        return None


def _parse_result(raw_text: str) -> dict:
    json_text = _extract_json(raw_text)
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        repaired = _repair_truncated_json(json_text)
        if repaired is None:
            raise
        parsed = json.loads(repaired)
    if 'fichiers' not in parsed or not isinstance(parsed['fichiers'], list):
        raise ValueError('Réponse IA mal structurée (fichiers manquants)')
    return {
        'statut': 'pret',
        'code': json.dumps(parsed, ensure_ascii=False, indent=2),
        'comprehension': parsed.get('comprehension', ''),
        'plan': parsed.get('plan', []),
        'description': parsed.get('description', ''),
        'stack': parsed.get('stack', ''),
        'fichiers': parsed['fichiers'],
        'tables': parsed.get('tables', []),
        'avertissements': _verifier_fichiers(parsed['fichiers']),
        'decisions_a_retenir': parsed.get('decisions_a_retenir', [])
    }


def _generate_claude(prompt: str, history=None, image=None) -> dict:
    api_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not api_key:
        return {'statut': 'erreur', 'message': 'Clé ANTHROPIC_API_KEY non configurée.'}
    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
        messages = list(history) if history else []

        if image:
            user_content = [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': image['mediaType'], 'data': image['data']}},
                {'type': 'text', 'text': prompt}
            ]
        else:
            user_content = prompt

        messages.append({'role': 'user', 'content': user_content})
        response = client.messages.create(
            model='claude-sonnet-4-5',
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        return _parse_result(response.content[0].text)
    except Exception as e:
        return {'statut': 'erreur', 'message': str(e)}


def _generate_openai(prompt: str, history=None, image=None) -> dict:
    api_key = os.environ.get('OPENAI_API_KEY', '').strip()
    if not api_key:
        return {'statut': 'erreur', 'message': 'Clé OPENAI_API_KEY non configurée.'}
    try:
        client = openai.OpenAI(api_key=api_key, timeout=60.0)
        messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        if history:
            messages.extend(history)

        if image:
            user_content = [
                {'type': 'text', 'text': prompt},
                {'type': 'image_url', 'image_url': {'url': f"data:{image['mediaType']};base64,{image['data']}"}}
            ]
        else:
            user_content = prompt

        messages.append({'role': 'user', 'content': user_content})
        response = client.chat.completions.create(
            model='gpt-4o',
            max_tokens=16000,
            messages=messages
        )
        return _parse_result(response.choices[0].message.content)
    except Exception as e:
        return {'statut': 'erreur', 'message': str(e)}


def _generate_gemini(prompt: str, history=None, image=None) -> dict:
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key:
        return {'statut': 'erreur', 'message': 'Clé GEMINI_API_KEY non configurée.'}
    try:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}'
        contents = []
        if history:
            for h in history:
                gemini_role = 'model' if h['role'] == 'assistant' else 'user'
                contents.append({'role': gemini_role, 'parts': [{'text': h['content']}]})

        full_prompt = f'{SYSTEM_PROMPT}\n\n{prompt}' if not history else prompt
        parts = [{'text': full_prompt}]
        if image:
            parts.append({'inline_data': {'mime_type': image['mediaType'], 'data': image['data']}})

        contents.append({'role': 'user', 'parts': parts})
        response = requests.post(url, json={'contents': contents}, timeout=60)
        data = response.json()
        if 'candidates' not in data:
            return {'statut': 'erreur', 'message': f'Erreur API Gemini: {data}'}
        text = data['candidates'][0]['content']['parts'][0]['text']
        return _parse_result(text)
    except Exception as e:
        return {'statut': 'erreur', 'message': str(e)}


def _generate_mistral(prompt: str, history=None, image=None) -> dict:
    api_key = os.environ.get('MISTRAL_API_KEY', '').strip()
    if not api_key:
        return {'statut': 'erreur', 'message': 'Clé MISTRAL_API_KEY non configurée.'}
    try:
        messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        if history:
            messages.extend(history)
        messages.append({'role': 'user', 'content': prompt})
        response = requests.post(
            'https://api.mistral.ai/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={'model': 'mistral-small-latest', 'messages': messages, 'max_tokens': 8000},
            timeout=180
        )
        data = response.json()
        if 'choices' not in data:
            return {'statut': 'erreur', 'message': f'Erreur API Mistral: {data}'}
        text = data['choices'][0]['message']['content']
        return _parse_result(text)
    except Exception as e:
        return {'statut': 'erreur', 'message': str(e)}


def _generate_demo(prompt: str, history=None, image=None) -> dict:
    """Mode secours sans cle API: genere un template professionnel adapte au prompt."""
    p = prompt.lower()

    css_base = """* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, -apple-system, sans-serif; background: #f4f3ec; color: #2b2410; line-height: 1.6; }
.btn { display: inline-block; padding: 0.8rem 1.6rem; background: #6366f1; color: #fff; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; text-decoration: none; transition: opacity 0.2s; }
.btn:hover { opacity: 0.9; }
.card { background: #fff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); padding: 2rem; }"""

    if any(k in p for k in ['connexion', 'login', 'authentification', 'se connecter']):
        html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Connexion - GNB41 IA</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="auth-wrap">
    <form class="card auth-card" id="loginForm">
      <h1>Connexion</h1>
      <label>Email<input type="email" name="email" required placeholder="vous@exemple.com"></label>
      <label>Mot de passe<input type="password" name="password" required placeholder="********"></label>
      <button type="submit" class="btn">Se connecter</button>
      <p class="auth-link"><a href="#">Mot de passe oublie ?</a></p>
    </form>
  </div>
  <script src="script.js"></script>
</body>
</html>"""
        css = css_base + """
.auth-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 1rem; }
.auth-card { width: 100%; max-width: 380px; }
.auth-card h1 { margin-bottom: 1.5rem; font-size: 1.6rem; text-align: center; }
.auth-card label { display: block; margin-bottom: 1rem; font-size: 0.9rem; font-weight: 600; }
.auth-card input { width: 100%; margin-top: 0.4rem; padding: 0.7rem; border: 1px solid #ddd6c7; border-radius: 8px; font-size: 1rem; }
.auth-card .btn { width: 100%; margin-top: 0.5rem; }
.auth-link { text-align: center; margin-top: 1rem; font-size: 0.9rem; }
.auth-link a { color: #6366f1; text-decoration: none; }"""
        js = """document.getElementById('loginForm').addEventListener('submit', function(e) {
  e.preventDefault();
  alert('Ceci est une demo GNB41 IA. Connectez une vraie cle API pour une authentification fonctionnelle.');
});"""
        desc = "Page de connexion professionnelle (demo GNB41 IA)"

    elif any(k in p for k in ['tableau de bord', 'dashboard', 'admin']):
        html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Tableau de bord - GNB41 IA</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="dash-layout">
    <aside class="sidebar">
      <h2>GNB41 IA</h2>
      <nav><a href="#" class="active">Accueil</a><a href="#">Statistiques</a><a href="#">Parametres</a></nav>
    </aside>
    <main>
      <h1>Tableau de bord</h1>
      <div class="stats-grid">
        <div class="card stat"><span class="stat-num">1 248</span><span class="stat-label">Utilisateurs</span></div>
        <div class="card stat"><span class="stat-num">3 502</span><span class="stat-label">Ventes</span></div>
        <div class="card stat"><span class="stat-num">89%</span><span class="stat-label">Satisfaction</span></div>
      </div>
    </main>
  </div>
  <script src="script.js"></script>
</body>
</html>"""
        css = css_base + """
.dash-layout { display: flex; min-height: 100vh; }
.sidebar { width: 220px; background: #2b2410; color: #f4f3ec; padding: 1.5rem; flex-shrink: 0; }
.sidebar h2 { margin-bottom: 2rem; font-size: 1.2rem; }
.sidebar nav { display: flex; flex-direction: column; gap: 0.6rem; }
.sidebar a { color: #d8d0b8; text-decoration: none; padding: 0.6rem 0.8rem; border-radius: 6px; }
.sidebar a.active, .sidebar a:hover { background: #6366f1; color: #fff; }
main { flex: 1; padding: 2rem; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-top: 1.5rem; }
.stat { text-align: center; }
.stat-num { display: block; font-size: 2rem; font-weight: 700; color: #6366f1; }
.stat-label { display: block; margin-top: 0.4rem; color: #6b6375; }"""
        js = """console.log('Dashboard demo GNB41 IA charge.');"""
        desc = "Tableau de bord administrateur (demo GNB41 IA)"

    elif any(k in p for k in ['boutique', 'e-commerce', 'ecommerce', 'panier', 'catalogue']):
        nav = """<nav class="shop-nav">
    <a href="index.html" class="logo">GNB41 Boutique</a>
    <div class="nav-links">
      <a href="index.html">Accueil</a>
      <a href="panier.html">Panier <span id="cart-count" class="cart-badge">0</span></a>
      <a href="connexion.html" id="nav-auth">Connexion</a>
      <a href="parametres.html">Parametres</a>
    </div>
  </nav>"""

        index_html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GNB41 Boutique</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  """ + nav + """
  <main class="products">
    <div class="card product" data-id="1" data-name="Produit 1" data-price="29.99">
      <div class="product-img"></div><h3>Produit 1</h3><p class="price">29,99 EUR</p>
      <button class="btn add-to-cart">Ajouter au panier</button>
    </div>
    <div class="card product" data-id="2" data-name="Produit 2" data-price="49.99">
      <div class="product-img"></div><h3>Produit 2</h3><p class="price">49,99 EUR</p>
      <button class="btn add-to-cart">Ajouter au panier</button>
    </div>
    <div class="card product" data-id="3" data-name="Produit 3" data-price="19.99">
      <div class="product-img"></div><h3>Produit 3</h3><p class="price">19,99 EUR</p>
      <button class="btn add-to-cart">Ajouter au panier</button>
    </div>
    <div class="card product" data-id="4" data-name="Produit 4" data-price="39.99">
      <div class="product-img"></div><h3>Produit 4</h3><p class="price">39,99 EUR</p>
      <button class="btn add-to-cart">Ajouter au panier</button>
    </div>
  </main>
  <script src="shop.js"></script>
</body>
</html>"""

        connexion_html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Connexion - GNB41 Boutique</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  """ + nav + """
  <div class="auth-wrap">
    <form class="card auth-card" id="loginForm">
      <h1 id="auth-title">Connexion</h1>
      <label id="label-nom" style="display:none;">Nom<input type="text" id="reg-nom" placeholder="Votre nom"></label>
      <label>Email<input type="email" id="auth-email" required placeholder="vous@exemple.com"></label>
      <label>Mot de passe<input type="password" id="auth-password" required placeholder="********"></label>
      <button type="submit" class="btn">Se connecter</button>
      <p class="auth-link"><a href="#" id="toggle-auth">Pas de compte ? S'inscrire</a></p>
    </form>
  </div>
  <script src="shop.js"></script>
</body>
</html>"""

        panier_html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Panier - GNB41 Boutique</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  """ + nav + """
  <main class="cart-page">
    <h1>Votre panier</h1>
    <div id="cart-items" class="cart-items"></div>
    <div class="cart-total">
      <span>Total :</span><span id="cart-total-amount">0,00 EUR</span>
    </div>
    <button class="btn" id="checkout-btn">Passer la commande</button>
  </main>
  <script src="shop.js"></script>
</body>
</html>"""

        parametres_html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Parametres - GNB41 Boutique</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  """ + nav + """
  <div class="auth-wrap">
    <div class="card auth-card">
      <h1>Parametres du compte</h1>
      <p id="settings-info" class="settings-info">Vous n'etes pas connecte.</p>
      <button class="btn" id="logout-btn" style="display:none;">Se deconnecter</button>
    </div>
  </div>
  <script src="shop.js"></script>
</body>
</html>"""

        css = css_base + """
.shop-nav { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.5rem; background: #fff; border-bottom: 1px solid #ddd6c7; flex-wrap: wrap; gap: 0.8rem; }
.shop-nav .logo { font-weight: 700; font-size: 1.1rem; color: #2b2410; text-decoration: none; }
.nav-links { display: flex; gap: 1.2rem; align-items: center; }
.nav-links a { color: #2b2410; text-decoration: none; font-size: 0.95rem; }
.nav-links a:hover { color: #6366f1; }
.cart-badge { background: #6366f1; color: #fff; border-radius: 999px; padding: 0.1rem 0.5rem; font-size: 0.75rem; margin-left: 0.2rem; }
.products { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; padding: 2rem; }
.product { text-align: center; }
.product-img { height: 130px; background: #ecdfb2; border-radius: 8px; margin-bottom: 1rem; }
.product h3 { margin-bottom: 0.3rem; }
.price { color: #6b6375; margin-bottom: 1rem; font-weight: 600; }
.auth-wrap { min-height: 70vh; display: flex; align-items: center; justify-content: center; padding: 1.5rem; }
.auth-card { width: 100%; max-width: 380px; }
.auth-card h1 { margin-bottom: 1.5rem; font-size: 1.6rem; text-align: center; }
.auth-card label { display: block; margin-bottom: 1rem; font-size: 0.9rem; font-weight: 600; }
.auth-card input { width: 100%; margin-top: 0.4rem; padding: 0.7rem; border: 1px solid #ddd6c7; border-radius: 8px; font-size: 1rem; }
.auth-card .btn { width: 100%; margin-top: 0.5rem; }
.auth-link { text-align: center; margin-top: 1rem; font-size: 0.9rem; }
.auth-link a { color: #6366f1; text-decoration: none; }
.settings-info { text-align: center; margin-bottom: 1rem; color: #6b6375; }
.cart-page { max-width: 700px; margin: 0 auto; padding: 2rem 1.5rem; }
.cart-items { display: flex; flex-direction: column; gap: 0.8rem; margin: 1.5rem 0; }
.cart-item { display: flex; justify-content: space-between; align-items: center; background: #fff; border: 1px solid #ddd6c7; border-radius: 8px; padding: 0.8rem 1rem; }
.cart-item button { background: none; border: none; color: #ef4444; cursor: pointer; font-size: 0.9rem; }
.cart-total { display: flex; justify-content: space-between; font-size: 1.2rem; font-weight: 700; padding: 1rem 0; border-top: 2px solid #ddd6c7; }
.cart-empty { text-align: center; color: #6b6375; padding: 2rem 0; }"""

        js = """(function() {
  function getCart() { return JSON.parse(localStorage.getItem('gnb41_cart') || '[]'); }
  function setCart(c) { localStorage.setItem('gnb41_cart', JSON.stringify(c)); updateCartCount(); }
  function getUser() { return JSON.parse(localStorage.getItem('gnb41_user') || 'null'); }
  function setUser(u) { localStorage.setItem('gnb41_user', JSON.stringify(u)); }
  function updateCartCount() {
    var el = document.getElementById('cart-count');
    if (el) { var c = getCart(); el.textContent = c.reduce(function(s,i){return s+i.qty;}, 0); }
  }
  function updateNavAuth() {
    var el = document.getElementById('nav-auth');
    var u = getUser();
    if (el && u) { el.textContent = u.nom || u.email; }
  }
  document.querySelectorAll('.add-to-cart').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var card = btn.closest('.product');
      var id = card.dataset.id, name = card.dataset.name, price = parseFloat(card.dataset.price);
      var cart = getCart();
      var existing = cart.find(function(i){return i.id === id;});
      if (existing) { existing.qty += 1; } else { cart.push({id: id, name: name, price: price, qty: 1}); }
      setCart(cart);
      btn.textContent = 'Ajoute !';
      setTimeout(function(){ btn.textContent = 'Ajouter au panier'; }, 1000);
    });
  });
  var cartItemsEl = document.getElementById('cart-items');
  if (cartItemsEl) {
    function renderCart() {
      var cart = getCart();
      if (cart.length === 0) { cartItemsEl.innerHTML = '<p class="cart-empty">Votre panier est vide.</p>'; }
      else {
        cartItemsEl.innerHTML = cart.map(function(i) {
          return '<div class="cart-item"><span>' + i.name + ' x' + i.qty + '</span><span>' + (i.price*i.qty).toFixed(2) + ' EUR <button data-id="' + i.id + '">Retirer</button></span></div>';
        }).join('');
        cartItemsEl.querySelectorAll('button').forEach(function(b) {
          b.addEventListener('click', function() {
            var cart2 = getCart().filter(function(i){return i.id !== b.dataset.id;});
            setCart(cart2); renderCart();
          });
        });
      }
      var total = cart.reduce(function(s,i){return s+i.price*i.qty;}, 0);
      var totalEl = document.getElementById('cart-total-amount');
      if (totalEl) totalEl.textContent = total.toFixed(2) + ' EUR';
    }
    renderCart();
    var checkoutBtn = document.getElementById('checkout-btn');
    if (checkoutBtn) checkoutBtn.addEventListener('click', function() {
      if (getCart().length === 0) { alert('Votre panier est vide.'); return; }
      alert('Commande simulee (demo GNB41 IA). Connectez une vraie cle API pour un vrai systeme de commande.');
      setCart([]); renderCart();
    });
  }
  var loginForm = document.getElementById('loginForm');
  if (loginForm) {
    var isRegister = false;
    var toggle = document.getElementById('toggle-auth');
    toggle.addEventListener('click', function(e) {
      e.preventDefault();
      isRegister = !isRegister;
      document.getElementById('auth-title').textContent = isRegister ? 'Inscription' : 'Connexion';
      document.getElementById('label-nom').style.display = isRegister ? 'block' : 'none';
      toggle.textContent = isRegister ? 'Deja un compte ? Se connecter' : "Pas de compte ? S'inscrire";
      loginForm.querySelector('button[type=submit]').textContent = isRegister ? "S'inscrire" : 'Se connecter';
    });
    loginForm.addEventListener('submit', function(e) {
      e.preventDefault();
      var email = document.getElementById('auth-email').value;
      var nom = document.getElementById('reg-nom') ? document.getElementById('reg-nom').value : '';
      setUser({ email: email, nom: nom || email.split('@')[0] });
      alert('Connexion simulee (demo GNB41 IA).');
      window.location.href = 'index.html';
    });
  }
  var settingsInfo = document.getElementById('settings-info');
  if (settingsInfo) {
    var u = getUser();
    if (u) {
      settingsInfo.textContent = 'Connecte en tant que ' + (u.nom || u.email) + ' (' + u.email + ')';
      document.getElementById('logout-btn').style.display = 'inline-block';
      document.getElementById('logout-btn').addEventListener('click', function() {
        localStorage.removeItem('gnb41_user');
        window.location.href = 'index.html';
      });
    }
  }
  updateCartCount();
  updateNavAuth();
})();"""

        readme = """# Boutique en ligne complete (demo GNB41 IA)

Boutique demo multi-pages avec navigation, panier interactif (localStorage), et systeme de connexion/inscription simule.

Pages :
- index.html : catalogue produits
- panier.html : panier avec ajout/suppression/total
- connexion.html : connexion et inscription
- parametres.html : profil du compte connecte

Ce projet a ete genere en mode demo car aucune cle API IA active n'a ete trouvee (absente ou credit epuise).
Pour activer la generation reelle et personnalisee par IA, configurez ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY ou MISTRAL_API_KEY dans le fichier .env du backend.

Prompt d'origine : """ + prompt

        desc = "Boutique en ligne complete avec navigation, panier et connexion (demo GNB41 IA)"
        fichiers = [
            {'chemin': 'index.html', 'contenu': index_html},
            {'chemin': 'connexion.html', 'contenu': connexion_html},
            {'chemin': 'panier.html', 'contenu': panier_html},
            {'chemin': 'parametres.html', 'contenu': parametres_html},
            {'chemin': 'style.css', 'contenu': css},
            {'chemin': 'shop.js', 'contenu': js},
            {'chemin': 'README.md', 'contenu': readme},
        ]
        return {
            'statut': 'pret',
            'code': json.dumps({'description': desc, 'stack': 'HTML/CSS/JS multi-pages', 'fichiers': fichiers}, ensure_ascii=False, indent=2),
            'description': desc,
            'stack': 'HTML/CSS/JS multi-pages',
            'fichiers': fichiers
        }



    elif any(k in p for k in ['portfolio', 'cv', 'profil']):
        html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Portfolio - GNB41 IA</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="hero"><h1>Votre Nom</h1><p>Developpeur / Createur</p></header>
  <main class="portfolio-grid">
    <div class="card"><h3>Projet 1</h3><p>Description courte du projet.</p></div>
    <div class="card"><h3>Projet 2</h3><p>Description courte du projet.</p></div>
  </main>
  <script src="script.js"></script>
</body>
</html>"""
        css = css_base + """
.hero { text-align: center; padding: 4rem 2rem; background: linear-gradient(135deg, #6366f1, #a855f7); color: #fff; }
.hero h1 { font-size: 2.2rem; margin-bottom: 0.5rem; }
.portfolio-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.5rem; padding: 2rem; }"""
        js = """console.log('Portfolio demo GNB41 IA charge.');"""
        desc = "Site portfolio (demo GNB41 IA)"

    elif any(k in p for k in ['landing', 'atterrissage', 'promo', 'marketing', 'lancement']):
        html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Landing Page - GNB41 IA</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="hero-lp">
    <h1>Votre produit, enfin simplifie</h1>
    <p>Une solution moderne pour resoudre votre probleme en quelques clics.</p>
    <a href="#" class="btn btn-lg">Commencer gratuitement</a>
  </header>
  <section class="features">
    <div class="card feature-card"><div class="feature-icon">&#9889;</div><h3>Rapide</h3><p>Des resultats en quelques secondes, sans configuration complexe.</p></div>
    <div class="card feature-card"><div class="feature-icon">&#128274;</div><h3>Securise</h3><p>Vos donnees sont protegees a chaque etape.</p></div>
    <div class="card feature-card"><div class="feature-icon">&#9989;</div><h3>Fiable</h3><p>Une infrastructure solide, disponible 24/7.</p></div>
  </section>
  <section class="cta-section">
    <h2>Pret a commencer ?</h2>
    <p>Rejoignez des milliers d'utilisateurs satisfaits des aujourd'hui.</p>
    <a href="#" class="btn btn-lg">Essayer gratuitement</a>
  </section>
  <footer class="footer-lp"><p>GNB41 IA - Tous droits reserves</p></footer>
  <script src="script.js"></script>
</body>
</html>"""
        css = css_base + """
.hero-lp { text-align: center; padding: 5rem 1.5rem; background: linear-gradient(135deg, #6366f1, #a855f7); color: #fff; }
.hero-lp h1 { font-size: 2.4rem; margin-bottom: 1rem; }
.hero-lp p { font-size: 1.1rem; margin-bottom: 2rem; opacity: 0.9; }
.btn-lg { padding: 1rem 2.2rem; font-size: 1.1rem; background: #fff; color: #6366f1; }
.features { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; padding: 3rem 2rem; max-width: 1000px; margin: 0 auto; }
.feature-card { text-align: center; }
.feature-icon { font-size: 2rem; margin-bottom: 0.8rem; }
.features h3 { margin-bottom: 0.6rem; color: #6366f1; font-size: 1.15rem; }
.features p { color: #6b6375; font-size: 0.95rem; }
.cta-section { text-align: center; padding: 3rem 1.5rem; background: #f4f3ec; }
.cta-section h2 { font-size: 1.6rem; margin-bottom: 0.6rem; }
.cta-section p { color: #6b6375; margin-bottom: 1.5rem; }
.footer-lp { text-align: center; padding: 2rem; color: #6b6375; font-size: 0.9rem; }"""
        js = """console.log('Landing page demo GNB41 IA chargee.');"""
        desc = "Landing page marketing (demo GNB41 IA)"

    elif any(k in p for k in ['blog', 'article', 'actualite']):
        html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blog - GNB41 IA</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="blog-header"><h1>Le Blog GNB41</h1></header>
  <main class="blog-list">
    <article class="card blog-post">
      <span class="post-date">15 aout 2026</span>
      <h2>Titre du premier article</h2>
      <p>Extrait de l'article presentant le sujet en quelques lignes accrocheuses pour donner envie de lire la suite.</p>
      <a href="#" class="btn">Lire la suite</a>
    </article>
    <article class="card blog-post">
      <span class="post-date">10 aout 2026</span>
      <h2>Titre du deuxieme article</h2>
      <p>Extrait de l'article presentant le sujet en quelques lignes accrocheuses pour donner envie de lire la suite.</p>
      <a href="#" class="btn">Lire la suite</a>
    </article>
  </main>
  <script src="script.js"></script>
</body>
</html>"""
        css = css_base + """
.blog-header { text-align: center; padding: 3rem 1.5rem; background: #2b2410; color: #f4f3ec; }
.blog-header h1 { font-size: 2rem; }
.blog-list { max-width: 700px; margin: 2rem auto; padding: 0 1.5rem; display: flex; flex-direction: column; gap: 1.5rem; }
.post-date { color: #6b6375; font-size: 0.85rem; }
.blog-post h2 { margin: 0.4rem 0 0.8rem; }
.blog-post p { color: #6b6375; margin-bottom: 1rem; }"""
        js = """console.log('Blog demo GNB41 IA charge.');"""
        desc = "Blog / articles (demo GNB41 IA)"

    elif any(k in p for k in ['formulaire de contact', 'contact', 'nous contacter']):
        html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Contact - GNB41 IA</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="contact-wrap">
    <form class="card contact-card" id="contactForm">
      <h1>Nous contacter</h1>
      <label>Nom<input type="text" name="nom" required placeholder="Votre nom"></label>
      <label>Email<input type="email" name="email" required placeholder="vous@exemple.com"></label>
      <label>Message<textarea name="message" required rows="5" placeholder="Votre message..."></textarea></label>
      <button type="submit" class="btn">Envoyer</button>
    </form>
  </div>
  <script src="script.js"></script>
</body>
</html>"""
        css = css_base + """
.contact-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 1rem; }
.contact-card { width: 100%; max-width: 480px; }
.contact-card h1 { margin-bottom: 1.5rem; font-size: 1.6rem; text-align: center; }
.contact-card label { display: block; margin-bottom: 1rem; font-size: 0.9rem; font-weight: 600; }
.contact-card input, .contact-card textarea { width: 100%; margin-top: 0.4rem; padding: 0.7rem; border: 1px solid #ddd6c7; border-radius: 8px; font-size: 1rem; font-family: inherit; resize: vertical; }
.contact-card .btn { width: 100%; margin-top: 0.5rem; }"""
        js = """document.getElementById('contactForm').addEventListener('submit', function(e) {
  e.preventDefault();
  alert('Ceci est une demo GNB41 IA. Connectez une vraie cle API pour un envoi fonctionnel.');
});"""
        desc = "Formulaire de contact (demo GNB41 IA)"

    elif any(k in p for k in ['liste de taches', 'todo', 'to-do', 'taches']):
        html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Taches - GNB41 IA</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="todo-wrap">
    <div class="card todo-card">
      <h1>Mes taches</h1>
      <form id="todoForm" class="todo-form">
        <input type="text" id="todoInput" placeholder="Nouvelle tache..." required>
        <button type="submit" class="btn">Ajouter</button>
      </form>
      <ul id="todoList" class="todo-list">
        <li><input type="checkbox"> <span>Exemple de tache</span></li>
      </ul>
    </div>
  </div>
  <script src="script.js"></script>
</body>
</html>"""
        css = css_base + """
.todo-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 1rem; }
.todo-card { width: 100%; max-width: 460px; }
.todo-card h1 { margin-bottom: 1.5rem; font-size: 1.6rem; text-align: center; }
.todo-form { display: flex; gap: 0.6rem; margin-bottom: 1.5rem; }
.todo-form input { flex: 1; padding: 0.7rem; border: 1px solid #ddd6c7; border-radius: 8px; font-size: 1rem; }
.todo-list { list-style: none; display: flex; flex-direction: column; gap: 0.6rem; }
.todo-list li { display: flex; align-items: center; gap: 0.6rem; padding: 0.6rem; background: #f4f3ec; border-radius: 8px; }"""
        js = """document.getElementById('todoForm').addEventListener('submit', function(e) {
  e.preventDefault();
  var input = document.getElementById('todoInput');
  var li = document.createElement('li');
  li.innerHTML = '<input type="checkbox"> <span>' + input.value + '</span>';
  document.getElementById('todoList').appendChild(li);
  input.value = '';
});"""
        desc = "Application de liste de taches (demo GNB41 IA)"

    else:
        html = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GNB41 IA</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="landing">
    <div class="card">
      <h1>Bienvenue sur GNB41 IA</h1>
      <p>Application generee en mode demo (aucune cle API active). Ajoutez une cle ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY ou MISTRAL_API_KEY pour activer la generation IA complete et personnalisee selon votre demande.</p>
      <a href="#" class="btn">En savoir plus</a>
    </div>
  </div>
  <script src="script.js"></script>
</body>
</html>"""
        css = css_base + """
.landing { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 1rem; }
.landing .card { max-width: 560px; text-align: center; }
.landing h1 { margin-bottom: 1rem; }
.landing p { margin-bottom: 1.5rem; color: #6b6375; }"""
        js = """console.log('GNB41 IA - mode demo charge.');"""
        desc = "GNB41 IA - Application demo (mode sans cle API)"

    readme = f"""# {desc}

Ce projet a ete genere en mode demo car aucune cle API IA active n'a ete trouvee (absente ou credit epuise).

Pour activer la generation reelle et personnalisee par IA, configurez au moins une des variables suivantes dans le fichier .env du backend :
- ANTHROPIC_API_KEY
- OPENAI_API_KEY
- GEMINI_API_KEY
- MISTRAL_API_KEY

Prompt d'origine : {prompt}"""

    fichiers = [
        {'chemin': 'index.html', 'contenu': html},
        {'chemin': 'style.css', 'contenu': css},
        {'chemin': 'script.js', 'contenu': js},
        {'chemin': 'README.md', 'contenu': readme},
    ]
    return {
        'statut': 'pret',
        'code': json.dumps({'description': desc, 'stack': 'HTML/CSS/JS statique', 'fichiers': fichiers}, ensure_ascii=False, indent=2),
        'description': desc,
        'stack': 'HTML/CSS/JS statique',
        'fichiers': fichiers
    }


PROVIDERS = {
    'claude': _with_retry(_generate_claude),
    'openai': _with_retry(_generate_openai),
    'gemini': _with_retry(_generate_gemini),
    'mistral': _with_retry(_generate_mistral),
}


def generate_project_code(prompt: str, provider: str = 'claude', history=None, image=None, contexte_projet: str = None, fichiers_connus=None) -> dict:
    """Génère une application structurée (multi-fichiers) via le fournisseur IA choisi."""
    if contexte_projet:
        entete = "[CONTEXTE - PROJET EXISTANT]" + chr(10)
        entete += "Ce projet contient deja les elements suivants. Ne les recree pas inutilement, "
        entete += "reste coherent avec l'existant, et ne modifie que ce qui est necessaire pour repondre a la demande." + chr(10)
        entete += contexte_projet + chr(10) + chr(10) + "[DEMANDE]" + chr(10)
        prompt = entete + prompt
    cle_par_provider = {
        'claude': 'ANTHROPIC_API_KEY',
        'openai': 'OPENAI_API_KEY',
        'gemini': 'GEMINI_API_KEY',
        'mistral': 'MISTRAL_API_KEY',
    }
    var_cle = cle_par_provider.get(provider)
    if not var_cle or not os.environ.get(var_cle, '').strip():
        return _generate_demo(prompt, history, image)

    func = PROVIDERS.get(provider)
    if func is None:
        return {'statut': 'erreur', 'message': f'Fournisseur inconnu: {provider}'}

    try:
        result = func(prompt, history, image)
        if result.get('statut') == 'pret' and 'fichiers' in result:
            result['avertissements'] = _verifier_fichiers(result['fichiers'], fichiers_connus)

            if fichiers_connus:
                nouveaux_chemins = {f.get('chemin') for f in result['fichiers']}
                supprimes = set(fichiers_connus) - nouveaux_chemins
                if supprimes:
                    result['avertissements'].append(
                        'Fichiers presents avant et absents apres generation: ' + ', '.join(sorted(supprimes))
                    )

            mots_suppression_voulue = ['supprim', 'retir', 'enlev', 'remplac', 'recre', 'reecri', 'refaire entierement']
            suppression_voulue = any(m in prompt.lower() for m in mots_suppression_voulue)

            def _extraire_corrigibles(avertissements):
                trouves = []
                for a in avertissements:
                    if 'Fichier vide' in a or 'Placeholder' in a:
                        trouves.append(a)
                    elif 'reference' in a and "n'est pas parmi les fichiers generes" in a:
                        trouves.append(a)
                    elif a.startswith('Fichiers presents avant et absents') and not suppression_voulue:
                        trouves.append(a)
                    elif a.startswith('Possible secret code en dur'):
                        trouves.append(a)
                return trouves

            historique_courant = list(history) if history else []
            dernier_prompt_envoye = prompt
            tentatives = 0
            max_tentatives = 1 if provider == 'mistral' else 2

            while True:
                corrigibles = _extraire_corrigibles(result.get('avertissements', []))
                if not corrigibles or tentatives >= max_tentatives:
                    if corrigibles:
                        result['avertissements'].append(
                            'Correction automatique non aboutie apres ' + str(tentatives) + ' tentative(s) - verification manuelle recommandee.'
                        )
                    break

                tentatives += 1
                correction_prompt = (
                    'Ta reponse precedente contient des problemes a corriger avant validation:' + chr(10)
                    + chr(10).join('- ' + c for c in corrigibles) + chr(10)
                    + 'IMPORTANT: ne te contente pas de decrire la correction dans un texte, effectue-la reellement. '
                    + 'Renvoie une nouvelle reponse JSON complete (meme format) avec le tableau "fichiers" contenant TOUS les fichiers du projet, '
                    + 'y compris chaque fichier CSS/JS/image reference par un lien ou une balise dans le HTML (link, script, img). '
                    + 'Un fichier reference mais absent du tableau "fichiers" est une erreur bloquante.'
                )
                historique_courant.append({'role': 'user', 'content': dernier_prompt_envoye})
                historique_courant.append({'role': 'assistant', 'content': result.get('code', '')})

                result_corrige = func(correction_prompt, historique_courant, None)
                if result_corrige.get('statut') != 'pret' or 'fichiers' not in result_corrige:
                    raison = result_corrige.get('message', 'reponse invalide') if result_corrige.get('statut') != 'pret' else 'fichiers absents de la reponse'
                    result['avertissements'].append(
                        'Tentative de correction ' + str(tentatives) + ' echouee (' + str(raison)[:200] + ') - verification manuelle recommandee.'
                    )
                    break

                result_corrige['avertissements'] = _verifier_fichiers(result_corrige['fichiers'], fichiers_connus)
                if fichiers_connus:
                    nouveaux_chemins_c = {f.get('chemin') for f in result_corrige['fichiers']}
                    supprimes_c = set(fichiers_connus) - nouveaux_chemins_c
                    if supprimes_c:
                        result_corrige['avertissements'].append(
                            'Fichiers presents avant et absents apres generation: ' + ', '.join(sorted(supprimes_c))
                        )
                result_corrige['comprehension'] = result_corrige.get('comprehension') or result.get('comprehension')
                result_corrige['plan'] = result_corrige.get('plan') or result.get('plan')

                result = result_corrige
                dernier_prompt_envoye = correction_prompt

        if result.get('statut') == 'erreur':
            msg = str(result.get('message', '')).lower()
            if 'credit' in msg or 'quota' in msg or '429' in msg or 'insufficient' in msg or 'non configurée' in msg:
                return _generate_demo(prompt, history, image)
        return result
    except json.JSONDecodeError as e:
        return {'statut': 'erreur', 'message': f'Réponse IA invalide (JSON): {str(e)}'}
