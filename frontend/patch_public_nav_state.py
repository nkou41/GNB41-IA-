with open('src/App.tsx', 'r') as f:
    content = f.read()

old = "const [showTemplatesGallery, setShowTemplatesGallery] = useState(false);"
new = """const [showTemplatesGallery, setShowTemplatesGallery] = useState(false);
  const [publicPage, setPublicPage] = useState<'accueil' | 'fonctionnalites' | 'tarifs' | 'apropos' | 'contact' | 'boutique' | null>(null);
  const [publicListings, setPublicListings] = useState<any[]>([]);"""

if old in content:
    content = content.replace(old, new)
    with open('src/App.tsx', 'w') as f:
        f.write(content)
    print("OK: etat navigation publique ajoute")
else:
    print("ERREUR: etat showTemplatesGallery non trouve")
