with open('app/services/generator.py', 'r') as f:
    content = f.read()

old = """    return {
        'statut': 'pret',
        'code': json.dumps(parsed, ensure_ascii=False, indent=2),
        'description': parsed.get('description', ''),
        'stack': parsed.get('stack', ''),
        'fichiers': parsed['fichiers']
    }"""

new = """    return {
        'statut': 'pret',
        'code': json.dumps(parsed, ensure_ascii=False, indent=2),
        'description': parsed.get('description', ''),
        'stack': parsed.get('stack', ''),
        'fichiers': parsed['fichiers'],
        'tables': parsed.get('tables', [])
    }"""

if old in content:
    content = content.replace(old, new)
    with open('app/services/generator.py', 'w') as f:
        f.write(content)
    print("OK: tables ajoutees au resultat de _parse_result")
else:
    print("ERREUR: bloc return original non trouve")
