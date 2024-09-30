from app import db, app

# Ensure the database is created within the app context
with app.app_context():
    db.create_all()
    print("Database tables created successfully.")
