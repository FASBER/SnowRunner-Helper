"""Fail build if a Windows wheel targets a different Python DLL/architecture.

The v0.31.1 CI accidentally built using Python 3.15 and an _rust.pyd
requiring python3t.dll, even though the workflow selected CPython 3.11.
"""
import importlib
import platform
import sys
from pathlib import Path


def verify():
    if sys.version_info[:2] != (3, 11) or platform.architecture()[0] != '64bit':
        raise RuntimeError(f'Expected 64-bit Python 3.11, got {sys.version}')
    import pefile  # installed as a PyInstaller dependency on Windows
    rust = importlib.import_module('cryptography.hazmat.bindings._rust')
    path = Path(rust.__file__)
    if path.suffix.lower() != '.pyd':
        raise RuntimeError(f'Unexpected Rust extension location: {path}')
    pe = pefile.PE(str(path), fast_load=True)
    try:
        pe.parse_data_directories(directories=[
            pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],
            pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT'],
        ])
        dlls = set()
        for name in ('DIRECTORY_ENTRY_IMPORT', 'DIRECTORY_ENTRY_DELAY_IMPORT'):
            for row in getattr(pe, name, []):
                dlls.add(row.dll.decode('ascii', errors='replace').lower())
    finally:
        pe.close()
    if 'python3t.dll' in dlls or 'python315.dll' in dlls:
        raise RuntimeError(f'Wrong cryptography Rust DLL dependencies: {sorted(dlls)}')
    if not dlls:
        raise RuntimeError('Cannot inspect cryptography Rust DLL imports')
    print('Safe Windows _rust.pyd imports:', ', '.join(sorted(dlls)))


if __name__ == '__main__':
    try:
        verify()
    except (OSError, ImportError, RuntimeError, ValueError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        raise SystemExit(1) from exc
