with open('src/App.tsx', 'r') as f:
    content = f.read()

old = '''          </div>
        )}
      </div>
    );
  }

  // Vue paramètres'''

new = '''          </div>
        )}
        <div style={{ padding: '1.5rem', textAlign: 'center', fontSize: '0.8rem', color: '#a89f8c' }}>
          <span style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => setShowLegal('cgv')}>Conditions Générales de Vente</span>
          {' · '}
          <span style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => setShowLegal('mentions')}>Mentions légales</span>
        </div>
      </div>
    );
  }

  // Vue paramètres'''

if old in content:
    content = content.replace(old, new)
    with open('src/App.tsx', 'w') as f:
        f.write(content)
    print("OK: liens CGV/mentions ajoutes au footer boutique")
else:
    print("ERREUR: fin de vue boutique non trouvee")
