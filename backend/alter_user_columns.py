from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    with db.engine.connect() as conn:
        for col_sql in [
            "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS pending_plan VARCHAR(30)",
            "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS pending_transaction_id INTEGER",
            "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS credits INTEGER DEFAULT 1",
        ]:
            conn.execute(text(col_sql))
            conn.commit()
            print(f"OK: {col_sql}")
    print("Colonnes ajoutees avec succes")
