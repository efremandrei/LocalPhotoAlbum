import os, uuid, traceback, platform, string
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, abort
from models import db, Album, Photo
from exif_utils import extract_exif_data
from config import Config

def ensure_schema():
    from sqlalchemy import text
    try:
        conn = db.engine.connect()
        cols = [r[1] for r in conn.execute(text('PRAGMA table_info(albums)')).fetchall()]
        if 'thumbnail_photo_id' not in cols:
            conn.execute(text('ALTER TABLE albums ADD COLUMN thumbnail_photo_id INTEGER'))
            conn.commit()
        conn.close()
    except Exception:
        pass

def create_app():
    app = Flask(__name__, instance_relative_config=True, static_folder='static', template_folder='templates')
    app.config.from_object(Config)
    os.makedirs(app.instance_path, exist_ok=True)

    # Logging
    logs_dir = Path(app.instance_path) / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    file_all = RotatingFileHandler(str(logs_dir / 'app.log'), maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    file_err = RotatingFileHandler(str(logs_dir / 'error.log'), maxBytes=2*1024*1024, backupCount=5, encoding='utf-8')
    fmt = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')
    file_all.setFormatter(fmt); file_err.setFormatter(fmt)
    file_all.setLevel(logging.DEBUG); file_err.setLevel(logging.ERROR)
    app.logger.setLevel(logging.INFO); app.logger.addHandler(file_all); app.logger.addHandler(file_err)
    root = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.setLevel(logging.INFO); root.addHandler(file_all); root.addHandler(file_err)

    db.init_app(app)
    with app.app_context():
        db.create_all(); ensure_schema()

    app.task_executor = ThreadPoolExecutor(max_workers=2); app.tasks = {}

    @app.before_request
    def before_request():
        try: app.logger.info(f'REQ {request.method} {request.path}')
        except Exception: pass

    @app.after_request
    def after_request(response):
        try: app.logger.info(f'RES {response.status_code} {request.method} {request.path}')
        except Exception: pass
        return response

    @app.context_processor
    def inject_sidebar():
        try:
            albums = Album.query.filter_by(archived=False).order_by(Album.name.asc()).all()
            album_id = None
            if request.view_args:
                if 'album_id' in request.view_args: album_id = int(request.view_args.get('album_id'))
                elif 'photo_id' in request.view_args:
                    pid = request.view_args.get('photo_id'); p = Photo.query.get(int(pid)) if pid is not None else None
                    album_id = p.album_id if p else None
            sidebar_days = []; current_album = None
            if album_id:
                current_album = Album.query.get(album_id)
                rows = db.session.query(Photo.day_label).filter(Photo.album_id==album_id, Photo.day_label.isnot(None)).distinct().order_by(Photo.day_label).all()
                sidebar_days = [r[0] for r in rows]
            return dict(sidebar_albums=albums, sidebar_days=sidebar_days, sidebar_current_album=current_album)
        except Exception:
            return dict(sidebar_albums=[], sidebar_days=[], sidebar_current_album=None)

    def is_allowed_image(path: Path) -> bool:
        return path.suffix in app.config['ALLOWED_EXTENSIONS']

    def add_photo_record(album: Album, img_path: Path, day_label=None):
        created_at, lat, lon = extract_exif_data(str(img_path))
        if created_at is None:
            try: created_at = datetime.fromtimestamp(img_path.stat().st_mtime)
            except Exception: created_at = None
        filename = img_path.name; user_title = os.path.splitext(filename)[0]
        photo = Photo(album_id=album.id, file_path=str(img_path.resolve()), filename=filename, day_label=day_label, user_title=user_title, created_at=created_at, gps_lat=lat, gps_lon=lon)
        db.session.add(photo); db.session.commit(); return 1

    def scan_album_dir(album_path: Path, album: Album):
        count = 0
        for img in sorted(album_path.glob('*')):
            if img.is_file() and is_allowed_image(img): count += add_photo_record(album, img, day_label=None)
        for sub in sorted([p for p in album_path.rglob('*') if p.is_dir()]):
            rel = sub.relative_to(album_path).as_posix()
            for img in sorted(sub.glob('*')):
                if img.is_file() and is_allowed_image(img): count += add_photo_record(album, img, day_label=rel)
        return count

    @app.route('/')
    def index(): return redirect(url_for('albums'))

    @app.get('/albums')
    def albums():
        all_albums = Album.query.filter_by(archived=False).order_by(Album.created_at.desc()).all()
        covers = {}
        for a in all_albums:
            pid = a.thumbnail_photo_id
            if pid is None:
                first = Photo.query.filter_by(album_id=a.id).order_by(Photo.created_at.asc(), Photo.id.asc()).first()
                pid = first.id if first else None
            covers[a.id] = pid
        return render_template('albums.html', albums=all_albums, covers=covers)

    @app.post('/api/albums/add')
    def api_albums_add():
        data = request.get_json(silent=True) or request.form
        path = (data.get('path') or '').strip().strip('"')
        if not path: return jsonify({'error':'Path is required'}), 400
        p = Path(path)
        if not p.exists() or not p.is_dir(): return jsonify({'error':'Directory not found'}), 404
        app.logger.info(f'Add album sync path={path}')
        album_name = p.name
        album = Album.query.filter_by(name=album_name).first()
        if album: album.path = str(p.resolve()); album.archived=False; db.session.commit()
        else: album = Album(name=album_name, path=str(p.resolve())); db.session.add(album); db.session.commit()
        Photo.query.filter_by(album_id=album.id).delete(); db.session.commit()
        cnt = scan_album_dir(p, album)
        if album.thumbnail_photo_id is None:
            first = Photo.query.filter_by(album_id=album.id).order_by(Photo.created_at.asc(), Photo.id.asc()).first()
            if first: album.thumbnail_photo_id = first.id; db.session.commit()
        return jsonify({'status':'ok','album_id':album.id,'album_name':album.name,'photos_scanned':cnt})

    @app.post('/api/albums/add_async')
    def api_albums_add_async():
        data = request.get_json(silent=True) or request.form
        path = (data.get('path') or '').strip().strip('"')
        if not path: return jsonify({'error':'Path is required'}), 400
        p = Path(path)
        if not p.exists() or not p.is_dir(): return jsonify({'error':'Directory not found'}), 404
        task_id = str(uuid.uuid4()); app.tasks[task_id] = {'state':'pending'}
        def run_task(album_path: Path):
            with app.app_context():
                try:
                    app.logger.info(f'Scan task started path={album_path}')
                    album_name = album_path.name
                    album = Album.query.filter_by(name=album_name).first()
                    if album: album.path = str(album_path.resolve()); album.archived=False; db.session.commit()
                    else: album = Album(name=album_name, path=str(album_path.resolve())); db.session.add(album); db.session.commit()
                    Photo.query.filter_by(album_id=album.id).delete(); db.session.commit()
                    cnt = scan_album_dir(album_path, album)
                    if album.thumbnail_photo_id is None:
                        first = Photo.query.filter_by(album_id=album.id).order_by(Photo.created_at.asc(), Photo.id.asc()).first()
                        if first: album.thumbnail_photo_id = first.id; db.session.commit()
                    app.logger.info(f'Scan task done album_id={album.id} photos={cnt}')
                    app.tasks[task_id] = {'state':'done','album_id':album.id,'album_name':album.name,'photos_scanned':cnt}
                except Exception as e:
                    app.logger.error('Scan task failed', exc_info=True)
                    app.tasks[task_id] = {'state':'error','message':str(e),'trace': traceback.format_exc()}
        app.task_executor.submit(run_task, p); return jsonify({'task_id': task_id})

    @app.get('/api/tasks/<task_id>')
    def api_task_status(task_id):
        info = app.tasks.get(task_id)
        if not info: return jsonify({'error':'unknown task'}), 404
        return jsonify(info)

    @app.post('/api/albums/<int:album_id>/remove')
    def api_albums_remove(album_id):
        data = request.get_json(silent=True) or request.form
        mode = (data.get('mode') or 'archive').lower()
        app.logger.info(f'Remove album id={album_id} mode={mode}')
        album = Album.query.get_or_404(album_id)
        if mode == 'archive': album.archived=True; db.session.commit(); return jsonify({'status':'ok','archived':True})
        elif mode == 'delete': Photo.query.filter_by(album_id=album.id).delete(); db.session.delete(album); db.session.commit(); return jsonify({'status':'ok','deleted':True})
        else: return jsonify({'error':'Invalid mode. Use \'archive\' or \'delete\'.'}), 400

    @app.patch('/api/albums/<int:album_id>/rename')
    def api_album_rename(album_id):
        from sqlalchemy.exc import IntegrityError
        album = Album.query.get_or_404(album_id)
        data = request.get_json(silent=True) or {}
        new_name = (data.get('name') or '').strip()
        if not new_name: app.logger.error('Rename failed: empty name'); return jsonify({'error':'Name required'}), 400
        old = album.name; album.name = new_name
        try: db.session.commit(); app.logger.info(f"Album renamed id={album.id} '{old}' -> '{new_name}'")
        except IntegrityError: db.session.rollback(); app.logger.error(f"Rename conflict for id={album.id} name='{new_name}'", exc_info=True); return jsonify({'error':'Album name already exists'}), 409
        except Exception: db.session.rollback(); app.logger.error('Rename failed (unexpected)', exc_info=True); return jsonify({'error':'Rename failed'}), 500
        return jsonify({'status':'ok','album_id':album.id,'name':album.name})

    @app.post('/api/albums/<int:album_id>/rename')
    def api_album_rename_post(album_id):
        from sqlalchemy.exc import IntegrityError
        album = Album.query.get_or_404(album_id)
        data = request.get_json(silent=True) or request.form
        new_name = (data.get('name') or '').strip()
        if not new_name: app.logger.error('Rename failed: empty name'); return jsonify({'error':'Name required'}), 400
        old = album.name; album.name = new_name
        try: db.session.commit(); app.logger.info(f"Album renamed id={album.id} '{old}' -> '{new_name}'")
        except IntegrityError: db.session.rollback(); app.logger.error(f"Rename conflict for id={album.id} name='{new_name}'", exc_info=True); return jsonify({'error':'Album name already exists'}), 409
        except Exception: db.session.rollback(); app.logger.error('Rename failed (unexpected)', exc_info=True); return jsonify({'error':'Rename failed'}), 500
        return jsonify({'status':'ok','album_id':album.id,'name':album.name})

    @app.patch('/api/albums/<int:album_id>/thumbnail')
    def api_album_thumbnail(album_id):
        album = Album.query.get_or_404(album_id)
        data = request.get_json(silent=True) or {}
        photo_id = data.get('photo_id')
        if not photo_id: return jsonify({'error':'photo_id required'}), 400
        photo = Photo.query.get_or_404(int(photo_id))
        if photo.album_id != album.id: return jsonify({'error':'Photo does not belong to this album'}), 400
        album.thumbnail_photo_id = photo.id; db.session.commit(); return jsonify({'status':'ok','thumbnail_photo_id':album.thumbnail_photo_id})

    @app.get('/api/albums/<int:album_id>/meta')
    def api_album_meta(album_id):
        album = Album.query.get_or_404(album_id)
        app.logger.info(f'Meta for album id={album.id}')
        photo_count = Photo.query.filter_by(album_id=album.id).count()
        return jsonify({'id':album.id,'name':album.name,'created_at': album.created_at.isoformat() if album.created_at else None,'photo_count':photo_count,'path':album.path})

    @app.get('/albums/<int:album_id>')
    def album_home(album_id):
        app.logger.info(f'Album home id={album_id}')
        album = Album.query.get_or_404(album_id)
        days = db.session.query(Photo.day_label).filter(Photo.album_id==album.id).distinct().order_by(Photo.day_label).all()
        day_labels = [d[0] for d in days if d[0]]
        photo_count = Photo.query.filter_by(album_id=album.id).count()
        return render_template('album.html', album=album, day_labels=day_labels, photo_count=photo_count)

    @app.get('/albums/<int:album_id>/all')
    def album_all(album_id):
        album = Album.query.get_or_404(album_id)
        photos = Photo.query.filter_by(album_id=album.id).order_by(Photo.created_at.asc(), Photo.id.asc()).all()
        groups = {}
        for p in photos:
            key = p.day_label or (p.created_at.date().isoformat() if p.created_at else 'Unknown')
            groups.setdefault(key, []).append(p)
        grouped = sorted(groups.items(), key=lambda kv: kv[0])
        return render_template('grid.html', album=album, grouped=grouped, mode='all')

    @app.get('/albums/<int:album_id>/day/<path:day_label>')
    def album_day(album_id, day_label):
        album = Album.query.get_or_404(album_id)
        photos = Photo.query.filter_by(album_id=album.id, day_label=day_label).order_by(Photo.created_at.asc(), Photo.id.asc()).all()
        grouped = [(day_label, photos)]
        return render_template('grid.html', album=album, grouped=grouped, mode='day')

    @app.get('/photos/<int:photo_id>')
    def photo_view(photo_id):
        photo = Photo.query.get_or_404(photo_id); album = photo.album
        context = request.args.get('context', 'all')
        day = context.split(':',1)[1] if context.startswith('day:') else None
        q = Photo.query.filter_by(album_id=album.id)
        if day: q = q.filter_by(day_label=day)
        photos = q.order_by(Photo.created_at.asc(), Photo.id.asc()).all()
        ids = [p.id for p in photos]; idx = ids.index(photo.id) if photo.id in ids else 0
        prev_id = ids[idx-1] if idx>0 else None; next_id = ids[idx+1] if idx < len(ids)-1 else None
        return render_template('photo.html', album=album, photo=photo, prev_id=prev_id, next_id=next_id, context=context)

    @app.get('/photo/raw/<int:photo_id>')
    def photo_raw(photo_id):
        photo = Photo.query.get_or_404(photo_id); path = Path(photo.file_path)
        if not path.exists(): abort(404)
        return send_file(str(path), as_attachment=False, download_name=photo.filename)

    @app.patch('/api/photos/<int:photo_id>')
    def api_update_photo(photo_id):
        app.logger.info(f'Update photo id={photo_id} fields={list((request.get_json(silent=True) or {}).keys())}')
        photo = Photo.query.get_or_404(photo_id); data = request.get_json(silent=True) or {}
        if 'user_title' in data: photo.user_title = data['user_title'] or None
        if 'user_description' in data: photo.user_description = data['user_description'] or None
        db.session.commit(); return jsonify({'status':'ok'})

    @app.get('/api/fs/list')
    def api_fs_list():
        sep = os.sep; start = Path.home()
        req_path = request.args.get('path', '').strip()
        if req_path:
            try:
                p = Path(req_path).expanduser().resolve(strict=True)
                if not p.is_dir(): return jsonify({'error':'Not a directory'}), 400
            except Exception: p = start
        else: p = start
        drives = []
        if platform.system().lower().startswith('win'):
            for letter in string.ascii_uppercase:
                root = Path(f'{letter}:/')
                if root.exists(): drives.append(str(root))
        def safe_listdir(path: Path):
            items = []
            try:
                for child in path.iterdir():
                    try:
                        if child.is_dir():
                            name = child.name
                            if name.startswith('.'): continue
                            items.append({'name': name, 'path': str(child.resolve())})
                    except Exception: continue
            except Exception: pass
            items.sort(key=lambda x: x['name'].lower()); return items
        parent = str(p.parent.resolve()) if p != p.parent else None
        return jsonify({'cwd':str(p), 'parent':parent, 'separator':sep, 'drives':drives, 'dirs': safe_listdir(p)})

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)