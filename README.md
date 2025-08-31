# Local Photo Album (Flask)

A local, Python-based photo album web app you run on your PC. It scans folders on your disk, saves EXIF + metadata in a SQLite database, and presents albums, daily groupings, and a full-screen viewer with navigation arrows and a map (if GPS exists).

> Designed for the folder layout you described: an **album folder** named like `Japan 2024` with **day subfolders** such as `2024-05-15`, `2024-05-16`, etc. You can also use albums without day subfolders—created dates will be inferred.

## Features

- **Albums page**
  - Add/rescan album by pointing to the folder on disk (e.g., `C:\Photos\Japan 2024`).
  - Remove album from the app (archive) or **remove & delete metadata** (DB only; your actual files remain untouched).
- **Album page**
  - *See all* photos or open a specific **Day**.
  - *See all* groups the grid by day (from folder name or file date).
- **Photo viewer**
  - Photo scales to fit (width or height) using `object-fit: contain`.
  - Left/right **overlay arrows** (and ← → keyboard) to navigate.
  - **Editable title** (defaults to filename without extension). Auto-saves.
  - **Description** box. Auto-saves.
  - Filename displayed in the corner.
  - **Leaflet map** with a marker if EXIF GPS exists.
- **Dark, high-contrast UI**—modern but not too bright.
- **Tech**: Flask, SQLAlchemy (SQLite), Pillow (EXIF), Leaflet (map).

## Quick Start (Windows / macOS / Linux)

1. **Install Python 3.9+**.
2. Open a terminal in the project folder and run:
   ```bash
   python -m venv .venv
   .venv/Scripts/activate        # Windows
   # source .venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```
3. **Run the app**:
   ```bash
   python app.py
   ```
   It starts on `http://127.0.0.1:5000` (or `http://localhost:5000`).

> The first run creates `instance/app.db` automatically.

## Usage

### Add an album
1. Go to **Albums**.
2. Paste the absolute folder path of your album (e.g., `C:\Photos\Japan 2024`) and click **Add / Rescan Album**.
3. The app scans:  
   - If there are subfolders (e.g., dates like `2024-05-15`), they are used as **day labels**.  
   - If there are no subfolders, it still imports any images in the root.
4. Titles default to **filename without extension**. EXIF date/GPS are read when available; otherwise file modified time is used.

### Remove an album
- **Remove (keep metadata)**: Album is archived (hidden) but DB rows remain. You can re-add the same folder later and keep your titles/notes if you wish (rescan currently refreshes photo rows; to keep old IDs, avoid delete mode).
- **Remove & delete metadata**: Deletes the album + photo metadata from the DB. **Files on disk are never deleted.**

### Edit title & description
- On the photo page, type in the title/description. Changes **auto-save** within ~0.5s.

### Navigation
- Click **See all** or a **Day** to view grids. Click any photo tile to open the viewer.
- Use the overlay arrows or your keyboard (← →) to navigate.

## Folder Layout Examples

```
C:\Photos\Japan 2024\
├── 2024-05-15\
│   ├── IMG_0001.JPG
│   └── IMG_0002.JPG
├── 2024-05-16\
│   ├── IMG_1001.JPG
│   └── IMG_1002.JPG
└── cover.png
```

or (no day folders):

```
/Users/you/Pictures/Japan 2024/
├── DSC00123.JPG
├── DSC00124.JPG
└── pano.png
```

## Map Tiles / Attribution

- The viewer uses **Leaflet** with the default OpenStreetMap tile server. The URL is configurable:
  - Set environment variable `TILE_URL_TEMPLATE` or edit `Config.TILE_URL_TEMPLATE` in `config.py`.
  - Default: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`
- Please respect the tile provider’s **terms of use** and attribution requirements. For heavy use, consider hosting tiles locally or using a paid provider.

## Supported Formats

- By default: `.jpg`, `.jpeg`, `.png`. (Add more in `Config.ALLOWED_EXTENSIONS` if you have the decoders installed.)

## Data Model (SQLite)

**Album**
- `id` (int, PK)
- `name` (str, unique)
- `path` (str, absolute album folder)
- `created_at` (datetime)
- `archived` (bool)

**Photo**
- `id` (int, PK)
- `album_id` (FK -> Album.id)
- `file_path` (absolute path to image on disk)
- `filename` (file name only)
- `day_label` (e.g., `YYYY-MM-DD`, derived from subfolder name)
- `user_title` (editable, defaults to filename without extension)
- `user_description` (editable notes)
- `created_at` (datetime from EXIF DateTimeOriginal or file mtime)
- `gps_lat`, `gps_lon` (floats if available)

## Notes & Tips

- **Rescan behavior**: Re-adding an album **rebuilds** its photo list from the folder, which resets metadata for those photos (IDs change). If you want a non-destructive rescan, this can be added later (e.g., reconcile by filename).
- **Security**: The app serves images from file paths stored in the DB and only after you add a folder. Avoid adding untrusted folders.
- **Performance**: For very large albums, consider pagination or lazy loading—straightforward to add.

## Customize

- UI variables live in `static/css/styles.css`.
- Map tile URL in `config.py`.
- Allowed extensions in `config.py`.

## License

This sample is provided as-is for local personal use. Leaflet and OpenStreetMap have their own licenses/terms.
