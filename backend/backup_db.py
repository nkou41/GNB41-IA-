import os
import shutil
from datetime import datetime

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'tableau_ia.db')
backup_dir = os.path.join(basedir, 'instance', 'backups')
os.makedirs(backup_dir, exist_ok=True)

if not os.path.exists(db_path):
    print(f"Base de donnees introuvable: {db_path}")
    exit(1)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_path = os.path.join(backup_dir, f'tableau_ia_{timestamp}.db')
shutil.copy2(db_path, backup_path)
print(f"Sauvegarde creee: {backup_path}")

backups = sorted(
    [f for f in os.listdir(backup_dir) if f.startswith('tableau_ia_') and f.endswith('.db')]
)
if len(backups) > 10:
    for old_backup in backups[:-10]:
        os.remove(os.path.join(backup_dir, old_backup))
        print(f"Ancienne sauvegarde supprimee: {old_backup}")
