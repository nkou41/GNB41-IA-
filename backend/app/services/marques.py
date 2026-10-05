import re
import unicodedata

# Liste non exhaustive : elle repère les cas évidents. Une détection met l'annonce en revue
# (elle n'est pas refusée). À compléter au fil des besoins.
MARQUES = [
    # Football : clubs, ligues, compétitions
    "Real Madrid", "FC Barcelone", "FC Barcelona", "Barça", "Atlético de Madrid", "Manchester United",
    "Manchester City", "Liverpool FC", "Chelsea FC", "Arsenal FC", "Tottenham", "Bayern Munich",
    "Borussia Dortmund", "Juventus", "AC Milan", "Inter Milan", "AS Roma", "Paris Saint-Germain", "PSG",
    "Olympique de Marseille", "Olympique Lyonnais", "AS Monaco", "Ajax Amsterdam", "Benfica",
    "FIFA", "UEFA", "Ligue 1", "Premier League", "La Liga", "Bundesliga",
    "Ligue des champions", "Champions League", "Ballon d'or",
    "EA Sports FC", "eFootball", "Football Manager",
    # Joueurs
    "Messi", "Cristiano Ronaldo", "Ronaldo", "Lewandowski", "Bellingham", "Mbappé", "Neymar", "Haaland", "Benzema", "Zidane", "Maradona",
    # Cinéma, séries, animation
    "Disney", "Pixar", "DreamWorks", "Warner Bros", "Marvel", "Avengers", "Spider-Man", "Batman", "Superman",
    "Star Wars", "Harry Potter", "Le Seigneur des anneaux", "Game of Thrones", "Squid Game", "Netflix",
    "Naruto", "Dragon Ball", "Pokémon", "Mickey Mouse", "Hello Kitty", "Shrek", "La Reine des neiges",
    "Fast and Furious", "James Bond", "Jurassic Park", "Toy Story", "Minions",
    # Jeux vidéo
    "Nintendo", "Super Mario", "Zelda", "Minecraft", "Fortnite", "Roblox", "GTA", "Call of Duty", "PUBG",
    "Free Fire", "Clash of Clans", "Clash Royale", "Candy Crush", "Angry Birds", "Among Us", "Pac-Man",
    "Tetris", "Temple Run", "Subway Surfers", "Sonic the Hedgehog", "League of Legends", "Fall Guys",
]


def _normaliser(texte):
    t = unicodedata.normalize('NFKD', texte or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', t).strip()


_NORMALISEES = [(m, ' ' + _normaliser(m) + ' ') for m in MARQUES]


def marques_detectees(*textes):
    """Liste des marques protégées trouvées (mots entiers, sans accents ni majuscules)."""
    contenu = ' ' + _normaliser(' '.join(t for t in textes if t)) + ' '
    trouvees = []
    for nom, motif in _NORMALISEES:
        if motif in contenu and nom not in trouvees:
            trouvees.append(nom)
    return trouvees
