#!/data/data/com.termux/files/usr/bin/sh
DATE=$(date +%Y%m%d_%H%M%S)
cp ~/tableau-ia/backend/instance/tableau_ia.db ~/tableau-ia/backend/backups/tableau_ia_$DATE.db
find ~/tableau-ia/backend/backups -name "*.db" -mtime +30 -delete
echo "Sauvegarde effectuee: tableau_ia_$DATE.db"
