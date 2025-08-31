import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    TILE_URL_TEMPLATE = os.environ.get(
        "TILE_URL_TEMPLATE",
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    )

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}

    SITE_AUTHOR = os.environ.get("SITE_AUTHOR", "Andrei Efr")
    SITE_CREATED_ON = os.environ.get("SITE_CREATED_ON", "2025-08-31")
