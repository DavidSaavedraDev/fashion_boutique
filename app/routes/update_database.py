# update_database.py
from app import create_app
from app.models1 import db

app = create_app()

with app.app_context():
    try:
        print("🔄 Actualizando base de datos...")
        
        # Agregar las nuevas columnas si no existen
        from sqlalchemy import text
        
        # Verificar y agregar cada columna si no existe
        columns_to_add = [
            'size VARCHAR(50) NULL',
            'color VARCHAR(50) NULL', 
            'material VARCHAR(100) NULL',
            'subcategory VARCHAR(100) NULL'
        ]
        
        for column_sql in columns_to_add:
            try:
                column_name = column_sql.split(' ')[0]
                db.session.execute(text(f"ALTER TABLE product ADD COLUMN {column_sql}"))
                print(f"✅ Columna {column_name} agregada")
            except Exception as e:
                if "Duplicate column name" in str(e) or "1060" in str(e):
                    print(f"ℹ️ Columna {column_name} ya existe")
                else:
                    print(f"⚠️ Error con columna {column_name}: {e}")
        
        db.session.commit()
        print("✅ Base de datos actualizada correctamente")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.session.rollback()