with open('app/models/listing.py', 'r') as f:
    content = f.read()

old = "    image_url = db.Column(db.String(500), nullable=True)"
new = "    image_url = db.Column(db.String(500), nullable=True)\n    categorie = db.Column(db.String(30), default='autre')\n    tags = db.Column(db.String(300), nullable=True)"

if old in content:
    content = content.replace(old, new)
    print("1/2 OK: colonnes categorie et tags ajoutees")
else:
    print("1/2 ERREUR: colonne image_url non trouvee")

old_dict = "            'image_url': self.image_url,"
new_dict = "            'image_url': self.image_url,\n            'categorie': self.categorie,\n            'tags': self.tags,"

if old_dict in content:
    content = content.replace(old_dict, new_dict)
    print("2/2 OK: to_dict mis a jour")
else:
    print("2/2 ERREUR: to_dict image_url non trouve")

with open('app/models/listing.py', 'w') as f:
    f.write(content)
