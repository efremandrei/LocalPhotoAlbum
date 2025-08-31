from PIL import Image, ExifTags
from datetime import datetime

def _ratio_to_float(ratio):
    try:
        return float(ratio[0]) / float(ratio[1]) if isinstance(ratio, tuple) else float(ratio)
    except Exception:
        return None

def _convert_to_degrees(value):
    try:
        d = _ratio_to_float(value[0]); m = _ratio_to_float(value[1]); s = _ratio_to_float(value[2])
        if None in (d, m, s): return None
        return d + (m/60.0) + (s/3600.0)
    except Exception:
        return None

def extract_exif_data(image_path):
    try:
        img = Image.open(image_path)
        exif = img._getexif()
        if not exif:
            return (None, None, None)

        tags = {ExifTags.TAGS.get(k,k): v for k,v in exif.items()}
        created_at = None
        dto = tags.get('DateTimeOriginal') or tags.get('DateTime')
        if dto:
            try:
                created_at = datetime.strptime(dto, "%Y:%m:%d %H:%M:%S")
            except Exception:
                created_at = None

        gps_info = tags.get('GPSInfo')
        lat = lon = None
        if gps_info:
            g = {ExifTags.GPSTAGS.get(k,k): v for k,v in gps_info.items()}
            lat_ref, lat_val = g.get('GPSLatitudeRef'), g.get('GPSLatitude')
            lon_ref, lon_val = g.get('GPSLongitudeRef'), g.get('GPSLongitude')
            if lat_val and lon_val and lat_ref and lon_ref:
                lat = _convert_to_degrees(lat_val)
                lon = _convert_to_degrees(lon_val)
                if lat is not None and lon is not None:
                    if lat_ref.upper()=='S': lat = -lat
                    if lon_ref.upper()=='W': lon = -lon
        return (created_at, lat, lon)
    except Exception:
        return (None, None, None)
