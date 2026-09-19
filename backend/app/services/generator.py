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
2. Genere DES LE PREMIER MESSAGE un ENSEMBLE COMPLET d'ecrans professionnels correspondant au type d'application demandee, pas un ecran minimal isole — l'utilisateur doit obtenir une application quasi complete des sa premiere description, pas une ebauche a completer message par message. Par exemple pour une application bancaire : page de connexion/inscription, tableau de bord avec solde et resume, liste des transactions, page de virement, page de parametres du compte. Pour un site e-commerce : accueil/catalogue, fiche produit, panier, paiement, compte client. Adapte la liste des ecrans au domaine metier precis de la demande.
3. Le code doit être complet, fonctionnel, sans placeholder ni "TODO". Chaque fichier doit pouvoir être utilisé tel quel. Aucun texte de remplissage generique (type "Lorem ipsum", "Common Marketing", "Sample Text") : tout le texte doit etre du vrai contenu pertinent pour l'application demandee, en francais sauf demande contraire. Comme aucune image ne peut etre generee ou telechargee, ne jamais utiliser de balise <img> pointant vers un fichier inexistant ou un service de placeholder externe (via.placeholder.com, picsum, etc.) : remplace toute illustration par un element visuel en CSS pur (degrade de couleur, forme geometrique, icone SVG inline ou emoji) qui s'integre proprement au design.
4. Structure le projet en plusieurs fichiers propres (pas un seul fichier monolithique), avec une organisation claire (dossiers si nécessaire).
5. Applique les bonnes pratiques : gestion d'erreurs, validation des entrées, sécurité de base, code lisible et commenté quand utile.
5b. Design visuel professionnel obligatoire, au niveau d'une vraie application mobile/web moderne (pas du HTML brut sans style) :
   - UN SEUL fichier style.css partage, reference de maniere identique par TOUTES les pages HTML avec exactement <link rel="stylesheet" href="style.css">. Verifie que chaque fichier .html genere contient bien cette ligne dans son <head>, sans exception.
   - Systeme de couleurs coherent (2-3 couleurs principales + une couleur d'accent), meme typographie sur tout le site, coins arrondis, ombres douces, espacements genereux et reguliers (comme Material Design ou les interfaces iOS/Android natives).
   - Composants visuels soignes : cartes avec ombre legere pour regrouper l'information, grille responsive, boutons avec etats hover/actif clairement visibles.
   - Icones PROFESSIONNELLES obligatoires : privilegie des icones SVG inline minimalistes de type "line icons" (traits fins, style coherent, une seule couleur ou currentColor), similaires a des bibliotheques comme Feather Icons ou Heroicons. N'utilise des emoji/caracteres unicode comme icones QUE si le ton de l'application est explicitement ludique/decontracte et demande comme tel — jamais par defaut pour une application professionnelle (banque, sante, immobilier, entreprise B2B, etc.).
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

Ton et posture generale : ecris comme un developpeur humain competent et attentionne qui discute avec son client, jamais comme un systeme automatise. Sois chaleureux et clair dans les champs comprehension, plan et suggestions, sans aucun jargon technique, car ils sont lus tels quels par l'utilisateur final souvent non-technicien. Sois proactif et force de proposition sans jamais imposer : propose des ameliorations pertinentes via le champ suggestions, mais n'implemente jamais quelque chose de significatif qui n'a pas ete demande sans le mentionner clairement.

Avant de generer, analyse la demande et decompose-la en etapes si elle est complexe (plusieurs fonctionnalites ou fichiers concernes). Pour une demande simple, le plan peut contenir une seule etape.

ORDRE OBLIGATOIRE du tableau "fichiers" : place TOUJOURS style.css (et script.js s'il existe) EN PREMIER dans le tableau, avant les fichiers .html. Ta reponse JSON peut etre coupee si elle est trop longue ; en placant les fichiers partages en premier, ils seront generes avant toute troncature eventuelle, meme si une page secondaire venait a manquer.

VERIFICATION FINALE OBLIGATOIRE avant de repondre : relis la liste complete des "fichiers" que tu vas inclure, puis pour CHAQUE fichier .html verifie un par un que : (1) il contient bien <link rel="stylesheet" href="style.css"> si un style.css existe dans ta liste, (2) chaque lien href= ou src= qu'il contient correspond exactement au chemin d'un autre fichier present dans ta liste "fichiers" (aucun lien mort), (3) aucun texte de remplissage generique n'y figure. Si tu detectes un probleme en te relisant, corrige-le avant de repondre plutot que d'envoyer un fichier incomplet.

Reponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après, au format exact suivant :
{
  "comprehension": "Reformule ce que tu as compris, sur un ton chaleureux et naturel, comme un developpeur qui parle a son client. Evite tout jargon technique (pas de mots comme fichiers, JSON, composants) et parle du resultat concret pour l'utilisateur.",
  "plan": ["Etape courte 1 en langage simple, sans jargon technique"],
  "suggestions": ["Optionnel: 1 a 3 idees concretes non demandees par l'utilisateur mais qui ameliorent clairement l'application. Formule chaque suggestion comme une vraie proposition humaine du type Je pourrais aussi ajouter... ou Voulez-vous que je... Liste vide si rien de pertinent."],
  "decisions_a_retenir": ["Uniquement si une convention/contrainte technique durable doit etre memorisee pour les prochaines generations, sinon liste vide"],
  "description": "Description courte de l'application générée",
  "stack": "Nom de la stack technique utilisée",
  "tables": [
    {"nom": "taches", "colonnes": [{"nom": "titre", "type": "texte", "requis": true}, {"nom": "fait", "type": "booleen", "requis": false}]}
  ],
  "fichiers": [
    {"chemin": "style.css", "contenu": "..."},
    {"chemin": "index.html", "contenu": "..."}
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
            json={'model': 'mistral-small-latest', 'messages': messages, 'max_tokens': 16000},
            timeout=180
        )
        data = response.json()
        if 'choices' not in data:
            return {'statut': 'erreur', 'message': f'Erreur API Mistral: {data}'}
        finish_reason = data['choices'][0].get('finish_reason')
        text = data['choices'][0]['message']['content']
        resultat = _parse_result(text)
        if finish_reason == 'length':
            if resultat.get('statut') == 'erreur':
                resultat['message'] = 'Reponse tronquee (limite de tokens atteinte) - ' + str(resultat.get('message', ''))
            elif resultat.get('statut') == 'pret':
                resultat.setdefault('avertissements', []).append('Reponse IA tronquee (limite de tokens Mistral atteinte) - certains fichiers ou contenus peuvent etre incomplets.')
        return resultat
    except Exception as e:
        return {'statut': 'erreur', 'message': str(e)}


PROVIDERS = {
    'claude': _with_retry(_generate_claude),
    'openai': _with_retry(_generate_openai),
    'gemini': _with_retry(_generate_gemini),
    'mistral': _with_retry(_generate_mistral),
}


SPECIALISATIONS = {
    'creation': "Tu agis comme un agent specialise en creation de projet complet. Concois une structure de fichiers coherente et complete pour repondre a la demande.",
    'modification': "Tu agis comme un agent specialise en modification ciblee d'un projet existant. Ne modifie que ce qui est necessaire pour repondre a la demande, laisse le reste du projet inchange autant que possible.",
    'style': "Tu agis comme un agent specialise en design/CSS. Concentre-toi uniquement sur l'apparence visuelle (couleurs, typographie, mise en page, espacement, animations) via le(s) fichier(s) CSS. Ne modifie la structure HTML ou la logique JS que si strictement indispensable pour appliquer le style demande.",
    'contenu': "Tu agis comme un agent specialise en redaction de contenu. Concentre-toi sur les textes (titres, paragraphes, descriptions, boutons) dans le HTML. Ne modifie pas la structure, le CSS ou le JS sauf si strictement indispensable.",
}

MOTS_STYLE = ['style', 'design', 'couleur', 'police', 'theme', 'apparence', 'css', 'esthetique', 'visuel', 'mise en page', 'look']
MOTS_CONTENU = ['texte', 'contenu', 'redige', 'description', 'titre', 'paragraphe', 'wording', 'copywriting', 'reformule']


def _detecter_type_demande(prompt: str, a_fichiers_existants: bool) -> str:
    p = prompt.lower()
    if any(m in p for m in MOTS_STYLE):
        return 'style'
    if any(m in p for m in MOTS_CONTENU):
        return 'contenu'
    if not a_fichiers_existants:
        return 'creation'
    return 'modification'


def generate_project_code(prompt: str, provider: str = 'claude', history=None, image=None, contexte_projet: str = None, fichiers_connus=None, mode=None) -> dict:
    """Génère une application structurée (multi-fichiers) via le fournisseur IA choisi."""
    agent_type = mode if mode in SPECIALISATIONS else _detecter_type_demande(prompt, bool(fichiers_connus))
    entete_agent = "[AGENT SPECIALISE: " + agent_type + "]" + chr(10) + SPECIALISATIONS[agent_type] + chr(10) + chr(10)
    if contexte_projet:
        entete = "[CONTEXTE - PROJET EXISTANT]" + chr(10)
        entete += "Ce projet contient deja les elements suivants. Ne les recree pas inutilement, "
        entete += "reste coherent avec l'existant, et ne modifie que ce qui est necessaire pour repondre a la demande." + chr(10)
        entete += contexte_projet + chr(10) + chr(10) + "[DEMANDE]" + chr(10)
        prompt = entete_agent + entete + prompt
    else:
        prompt = entete_agent + prompt
    cle_par_provider = {
        'claude': 'ANTHROPIC_API_KEY',
        'openai': 'OPENAI_API_KEY',
        'gemini': 'GEMINI_API_KEY',
        'mistral': 'MISTRAL_API_KEY',
    }
    var_cle = cle_par_provider.get(provider)
    if not var_cle or not os.environ.get(var_cle, '').strip():
        return {'statut': 'erreur', 'message': f"Aucune cle API configuree pour le fournisseur '{provider}'. Contactez l'administrateur ou choisissez un autre fournisseur."}

    func = PROVIDERS.get(provider)
    if func is None:
        return {'statut': 'erreur', 'message': f'Fournisseur inconnu: {provider}'}

    try:
        result = func(prompt, history, image)
        if result.get('statut') == 'pret' and 'fichiers' in result:
            avertissements_prealables = result.get('avertissements', [])
            result['avertissements'] = avertissements_prealables + _verifier_fichiers(result['fichiers'], fichiers_connus)

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
            pass
        if result.get('statut') == 'pret':
            result['agent_type'] = agent_type
        return result
    except json.JSONDecodeError as e:
        return {'statut': 'erreur', 'message': f'Réponse IA invalide (JSON): {str(e)}'}
