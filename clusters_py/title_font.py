"""Register the bundled title font privately for this application process."""
import ctypes
from pathlib import Path
import sys

TITLE_FONT = ('Nunito ExtraBold', 25)


def register_title_font():
    path = Path(__file__).with_name('assets') / 'fonts' / 'Nunito-ExtraBold.ttf'
    if not path.is_file():
        return False
    if sys.platform == 'darwin':
        cf = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        ct = ctypes.CDLL('/System/Library/Frameworks/CoreText.framework/CoreText')
        cf.CFURLCreateFromFileSystemRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                                              ctypes.c_long, ctypes.c_bool]
        cf.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        ct.CTFontManagerRegisterFontsForURL.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                                       ctypes.POINTER(ctypes.c_void_p)]
        ct.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool
        encoded = bytes(path)
        url = cf.CFURLCreateFromFileSystemRepresentation(None, encoded, len(encoded), False)
        if not url:
            return False
        error = ctypes.c_void_p()
        try:
            return bool(ct.CTFontManagerRegisterFontsForURL(url, 1, ctypes.byref(error)))
        finally:
            if error.value:
                cf.CFRelease(error)
            cf.CFRelease(url)
    return False
