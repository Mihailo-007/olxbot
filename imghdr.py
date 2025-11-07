# Replacement for the removed imghdr module (Python 3.13+)
import os

def what(file, h=None):
    if h is None:
        if isinstance(file, (str, bytes, os.PathLike)):
            with open(file, 'rb') as f:
                h = f.read(32)
        else:
            return None
    for k, v in tests:
        res = v(h)
        if res:
            return res
    return None

def test_jpeg(h):
    if h[6:10] in (b'JFIF', b'Exif'):
        return 'jpeg'

def test_png(h):
    if h.startswith(b'\211PNG\r\n\032\n'):
        return 'png'

def test_gif(h):
    if h[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'

def test_tiff(h):
    if h[:2] in (b'MM', b'II'):
        return 'tiff'

def test_bmp(h):
    if h.startswith(b'BM'):
        return 'bmp'

tests = [("jpeg", test_jpeg), ("png", test_png), ("gif", test_gif), ("tiff", test_tiff), ("bmp", test_bmp)]
