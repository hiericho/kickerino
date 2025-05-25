# KickChatter.spec

# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files # For CustomTkinter

block_cipher = None

# --- USER CONFIGURATION: YOU MUST ADJUST THESE ---
# Path to your MSYS2 MinGW (64-bit or 32-bit matching your Python) bin directory
# This is where cairocffi/cairosvg looks for its DLLs.
MSYS_MINGW_BIN_PATH = 'C:\\msys64\\mingw64\\bin'  # <--- !!! ADJUST THIS PATH !!!

# Optional: Path to your application's icon (.ico file)
APP_ICON_PATH = None
# ----------------------------------------------------


# --- Collect CustomTkinter data files ---
# This ensures themes and fonts for CustomTkinter are included.
customtkinter_datas = collect_data_files('customtkinter', include_py_files=False)
print(f"CustomTkinter data files collected: {customtkinter_datas}")


# --- List of Cairo and related DLLs to bundle ---
# These are common dependencies. Verify them against your MSYS_MINGW_BIN_PATH.
# The order doesn't strictly matter here.
cairo_dlls_to_bundle = [
    'libcairo-2.dll',
    'libfontconfig-1.dll',
    'libfreetype-6.dll',
    'libpixman-1-0.dll',
    'libpng16-16.dll',
    'zlib1.dll',
    'libexpat-1.dll',
    'libffi-8.dll',        # Or libffi-7.dll or similar, check your mingw bin
    'libglib-2.0-0.dll',
    'libgobject-2.0-0.dll',
    'libpcre2-8-0.dll',    # Or libpcre-1.dll for older GLib
    'libintl-8.dll',
    'libiconv-2.dll',
    # Potentially more depending on your exact GTK/Cairo stack from MSYS2
    # e.g., 'libharfbuzz-0.dll', 'libbrotlidec.dll', 'libbrotlicommon.dll'
    # 'libgraphite2.dll'
]
binaries_to_add = []
if os.path.isdir(MSYS_MINGW_BIN_PATH):
    for dll_name in cairo_dlls_to_bundle:
        dll_path = os.path.join(MSYS_MINGW_BIN_PATH, dll_name)
        if os.path.exists(dll_path):
            binaries_to_add.append((dll_path, '.'))  # Adds DLL to the root of the bundled app
            print(f"Found and adding DLL: {dll_path}")
        else:
            print(f"WARNING: Required DLL not found, skipping: {dll_path}. Badge rendering might fail.")
else:
    print(f"WARNING: MSYS_MINGW_BIN_PATH '{MSYS_MINGW_BIN_PATH}' not found. Cairo DLLs will not be bundled. Badge rendering will likely fail.")


a = Analysis(
    ['main.py'],  # Your main script
    pathex=['.'],  # Add current directory (project root) to pathex
    binaries=binaries_to_add,
    datas=customtkinter_datas,
    hiddenimports=[
        'customtkinter',
        'PIL._tkinter_finder', # Often needed for Pillow images in Tkinter
        'cairocffi',           # For cairosvg
        'cairosvg',            # For SVG rendering
        'badge_manager',       # Your custom module
        'channel_tab',         # Your custom module
        'kick_api',            # Your custom module
        'kick_chat',           # Your custom module
        # Add any other modules that PyInstaller might miss,
        # especially those imported dynamically or by dependencies.
        # For example, if using pkg_resources or importlib.metadata indirectly:
        # 'pkg_resources.py2_warn', 
        # 'importlib_metadata' # for Python < 3.8 if a library uses it
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False, # Usually False is fine
    cipher=block_cipher,
    noarchive=False, # False is default, set to True for specific advanced cases
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    # a.binaries, # Binaries from Analysis are automatically included if not overridden
    # a.zipfiles, # Usually just PYZ
    # a.datas,    # Datas from Analysis are automatically included if not overridden
    [], # Pass empty list if Analysis object handles binaries, datas, etc.
    name='KickChatter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False, # Stripping can sometimes cause issues, set to True for smaller exe if it works
    upx=False,    # UPX compression. Set to False if it causes issues or AV false positives.
    upx_exclude=[],
    runtime_tmpdir=None,  # Crucial for one-file: PyInstaller creates a temp dir at runtime.
                        # Set to a path string if you want a persistent temp dir (not common for one-file).
    console=False,        # GUI application, so no console window.
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,     # None = auto-detect (e.g., 'x86_64' or 'x86')
    codesign_identity=None,
    entitlements_plist=None,
    icon=APP_ICON_PATH,   # Set to your .ico file path or None
)

coll = COLLECT(
    exe, # The EXE object defined above
    a.binaries,
    a.datas,
    a.zipfiles, # Include this if your PYZ is separate
    strip=False,
    upx=False, # Start with UPX off for one-folder too for debugging
    upx_exclude=[],
    name='KickChatter' # This will be the name of the output folder
)