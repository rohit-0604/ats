"""Explicit local-file effects shared by the M0 store and CLI."""
from __future__ import annotations
import ctypes
import os
from pathlib import Path
import re
import stat
import tempfile
from app.baseline_contracts import MAX_INPUT, M0Error
def _drive_type(anchor: str) -> int:
    if os.name != 'nt':
        return 3
    return ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(anchor))
def validate_path(value: str | Path, *, exists: bool=False, database: bool=False) -> Path:
    try:
        raw = os.fspath(value)
        if not isinstance(raw, str) or not raw or '\0' in raw or raw.startswith(('\\', '//')) or '://' in raw:
            raise M0Error('PATH_POLICY')
        if re.match(r'^[A-Za-z]:(?![\\/])', raw):
            raise M0Error('PATH_POLICY')
        without_drive = raw[2:] if re.match(r'^[A-Za-z]:',raw) else raw
        if ':' in without_drive or '?' in raw or '*' in raw:
            raise M0Error('PATH_POLICY')
        for part in re.split(r'[\\/]',without_drive):
            if part in ('', '.', '..'):
                continue
            if part.endswith(('.', ' ')) or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?', part, re.I):
                raise M0Error('PATH_POLICY')
        supplied = Path(raw)
        joined = supplied if supplied.is_absolute() else Path.cwd() / supplied
        if _drive_type(joined.anchor) != 3:
            raise M0Error('PATH_POLICY')
        current = Path(joined.anchor)
        parts = joined.parts[1:]
        for i, part in enumerate(parts):
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                if i != len(parts)-1 or exists:
                    raise M0Error('PATH_POLICY') from None
                continue
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0) & 1024:
                raise M0Error('PATH_POLICY')
            if i < len(parts)-1 and not stat.S_ISDIR(info.st_mode):
                raise M0Error('PATH_POLICY')
            if i == len(parts)-1 and not stat.S_ISREG(info.st_mode):
                raise M0Error('PATH_POLICY')
        path = joined.resolve(strict=False)
        if not path.parent.is_dir() or database and path.suffix.lower() != '.sqlite3':
            raise M0Error('PATH_POLICY')
        return path
    except (OSError, ValueError, TypeError):
        raise M0Error('PATH_POLICY') from None
def read_bounded(value: str | Path, limit: int=MAX_INPUT) -> bytes:
    path = validate_path(value, exists=True)
    try:
        with path.open('rb') as f:
            raw = f.read(limit+1)
    except OSError:
        raise M0Error('STORE_FAILURE') from None
    if len(raw)>limit:
        raise M0Error('LIMIT_EXCEEDED')
    return raw
def write_export(value: str | Path, data: bytes) -> None:
    path = validate_path(value)
    if len(data)>MAX_INPUT:
        raise M0Error('LIMIT_EXCEEDED')
    temporary = None
    try:
        if path.exists():
            raise M0Error('OUTPUT_FAILURE')
        fd,name = tempfile.mkstemp(prefix='.m0_',suffix='.tmp',dir=path.parent)
        temporary = Path(name)
        with os.fdopen(fd,'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        validate_path(path)
        if os.name=='nt':
            os.rename(temporary,path)  # Windows rename never replaces.
        else:
            os.link(temporary,path)  # Exclusive publication for offline test portability.
            temporary.unlink()
        temporary=None
    except OSError:
        raise M0Error('OUTPUT_FAILURE') from None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass  # Only our own temporary file; a crash can leave it too.
