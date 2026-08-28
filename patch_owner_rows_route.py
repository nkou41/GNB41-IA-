with open('app/routes/appdb.py', 'r') as f:
    content = f.read()

old = "@appdb_bp.route('/tables/<table_id>', methods=['DELETE'])"
new = """@appdb_bp.route('/tables/<table_id>/rows', methods=['GET'])
@login_required
def owner_list_rows(table_id):
    table = AppTable.query.get_or_404(table_id)
    if not _check_project_access(table.project_id):
        return jsonify({'error': 'Non autorisé'}), 403
    rows = AppRow.query.filter_by(table_id=table_id).all()
    return jsonify([r.to_dict() for r in rows])


@appdb_bp.route('/tables/<table_id>', methods=['DELETE'])"""

if old in content:
    content = content.replace(old, new)
    with open('app/routes/appdb.py', 'w') as f:
        f.write(content)
    print("OK: route owner_list_rows ajoutee")
else:
    print("ERREUR: route delete_table originale non trouvee")
