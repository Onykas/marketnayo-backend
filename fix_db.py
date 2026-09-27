from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'preparation'"))
    conn.execute(text("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'proche'"))
    conn.commit()
    print('Statuts ajoutés avec succès !')