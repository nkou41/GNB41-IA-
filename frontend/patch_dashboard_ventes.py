with open('app/routes/marketplace.py', 'r') as f:
    content = f.read()

old = """    ventes_completes = Purchase.query.filter_by(statut='complete').all()
    total_ventes = len(ventes_completes)
    total_commission = sum(p.commission_centimes for p in ventes_completes)
    total_ca = sum(p.prix_paye_centimes for p in ventes_completes)

    return jsonify({
        'total_listings': total_listings,
        'listings_publies': listings_publies,
        'total_ventes': total_ventes,
        'total_commission_centimes': total_commission,
        'total_chiffre_affaires_centimes': total_ca
    })"""

new = """    ventes_completes = Purchase.query.filter_by(statut='complete').all()
    total_ventes = len(ventes_completes)
    total_commission = sum(p.commission_centimes for p in ventes_completes)
    total_ca = sum(p.prix_paye_centimes for p in ventes_completes)

    dernieres_ventes = Purchase.query.order_by(Purchase.created_at.desc()).limit(10).all()
    ventes_detail = []
    for p in dernieres_ventes:
        listing = Listing.query.get(p.listing_id)
        ventes_detail.append({
            'id': p.id,
            'titre': listing.titre if listing else 'Annonce supprimée',
            'prix_paye_centimes': p.prix_paye_centimes,
            'statut': p.statut,
            'created_at': p.created_at.isoformat()
        })

    return jsonify({
        'total_listings': total_listings,
        'listings_publies': listings_publies,
        'total_ventes': total_ventes,
        'total_commission_centimes': total_commission,
        'total_chiffre_affaires_centimes': total_ca,
        'dernieres_ventes': ventes_detail
    })"""

if old in content:
    content = content.replace(old, new)
    with open('app/routes/marketplace.py', 'w') as f:
        f.write(content)
    print("OK: dernieres ventes ajoutees au dashboard")
else:
    print("ERREUR: bloc dashboard original non trouve")
