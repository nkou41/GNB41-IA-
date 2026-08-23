with open('app/routes/marketplace.py', 'r') as f:
    content = f.read()

old = """            json={
                'description': f'GNB41 IA - {listing.titre}',
                'amount': montant_xof,
                'currency': {'iso': 'XOF'},
                'customer': {
                    'email': current_user.email,
                    'firstname': current_user.username,
                    'lastname': '.'
                }
            },"""

new = """            json={
                'description': f'GNB41 IA - {listing.titre}',
                'amount': montant_xof,
                'currency': {'iso': 'XOF'},
                'callback_url': f'http://localhost:5173/marketplace-callback?purchase_id={purchase.id}',
                'customer': {
                    'email': current_user.email,
                    'firstname': current_user.username,
                    'lastname': '.'
                }
            },"""

if old in content:
    content = content.replace(old, new)
    with open('app/routes/marketplace.py', 'w') as f:
        f.write(content)
    print("OK: callback_url ajoutee")
else:
    print("ERREUR: bloc json transaction non trouve")
