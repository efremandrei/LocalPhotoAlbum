from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Album(db.Model):
    __tablename__ = "albums"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    path = db.Column(db.String(1024), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    archived = db.Column(db.Boolean, default=False, nullable=False)
    thumbnail_photo_id = db.Column(db.Integer, nullable=True)

    photos = db.relationship("Photo", backref="album", cascade="all, delete-orphan")

class Photo(db.Model):
    __tablename__ = "photos"
    id = db.Column(db.Integer, primary_key=True)
    album_id = db.Column(db.Integer, db.ForeignKey("albums.id"), nullable=False)
    file_path = db.Column(db.String(2048), nullable=False)
    filename = db.Column(db.String(512), nullable=False)
    day_label = db.Column(db.String(64), nullable=True)
    user_title = db.Column(db.String(512), nullable=True)
    user_description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=True)
    gps_lat = db.Column(db.Float, nullable=True)
    gps_lon = db.Column(db.Float, nullable=True)
