with open('src/App.tsx', 'r') as f:
    content = f.read()

changes = 0

old_state = "const [publishFile, setPublishFile] = useState<File | null>(null);"
new_state = "const [publishFile, setPublishFile] = useState<File | null>(null);\n  const [publishImage, setPublishImage] = useState<File | null>(null);"

if old_state in content:
    content = content.replace(old_state, new_state)
    changes += 1
    print("1/4 OK: etat publishImage ajoute")
else:
    print("1/4 ERREUR: etat publishFile non trouve")

old_formdata_end = "      if (publishSourceType === 'externe_lien') formData.append('lien_externe', publishLienExterne);"
new_formdata_end = "      if (publishSourceType === 'externe_lien') formData.append('lien_externe', publishLienExterne);\n      if (publishImage) formData.append('image', publishImage);"

if old_formdata_end in content:
    content = content.replace(old_formdata_end, new_formdata_end)
    changes += 1
    print("2/4 OK: image ajoutee au FormData")
else:
    print("2/4 ERREUR: bloc FormData non trouve")

old_reset = "      setPublishFile(null);\n      const listings = await api.listMarketplace();"
new_reset = "      setPublishFile(null);\n      setPublishImage(null);\n      const listings = await api.listMarketplace();"

if old_reset in content:
    content = content.replace(old_reset, new_reset)
    changes += 1
    print("3/4 OK: reset publishImage ajoute")
else:
    print("3/4 ERREUR: bloc reset non trouve")

old_form_field = '''              <input placeholder="Prix (€)" type="number" step="0.01" min="0" value={publishPrix} onChange={(e) => setPublishPrix(e.target.value)} />

              <select value={publishSourceType}'''

new_form_field = '''              <input placeholder="Prix (€)" type="number" step="0.01" min="0" value={publishPrix} onChange={(e) => setPublishPrix(e.target.value)} />

              <label style={{ fontSize: '0.85rem', color: '#8a7f68' }}>
                Image de présentation (optionnel — sinon capture automatique pour les liens)
              </label>
              <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => setPublishImage(e.target.files?.[0] || null)} />

              <select value={publishSourceType}'''

if old_form_field in content:
    content = content.replace(old_form_field, new_form_field)
    changes += 1
    print("4/4 OK: champ upload image ajoute au formulaire")
else:
    print("4/4 ERREUR: bloc formulaire prix non trouve")

with open('src/App.tsx', 'w') as f:
    f.write(content)

print(f"\\nTotal: {changes}/4 modifications appliquees")
