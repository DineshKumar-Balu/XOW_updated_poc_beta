# Import necessary modules
import os
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

# Define paths to required binaries and data
tesseract_path = os.path.join(os.getcwd(), "Tesseract-OCR")
ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg-v1", "bin", "ffmpeg.exe")
tesseract_exe = os.path.join(tesseract_path, "tesseract.exe")  # Path to tesseract.exe
tesseract_data_path = os.path.join(tesseract_path, "tessdata")  # Path to tessdata
vlc_dll_path = os.path.join(os.getcwd(), "VLC", "libvlc.dll")  # Path to VLC's libvlc.dll
xow_logo_path = r"C:\Users\Intern_Account\Documents\Build-dir-finial\assets\XOW.png"  # Absolute path to XOW.png logo

# Specify binaries (executables)
binaries = [
    (ffmpeg_path, "ffmpeg-v1/bin"),  # FFmpeg binary
    (tesseract_exe, "Tesseract-OCR"),  
    (vlc_dll_path, "VLC")  # VLC DLL
]

# Specify data files
datas = [
    (tesseract_path, "Tesseract-OCR"),  # Full Tesseract folder
    (tesseract_data_path, "Tesseract-OCR/tessdata"),  # Tesseract data files
    (xow_logo_path, "assets"),  # Include XOW.png logo file in the assets folder
]

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[os.getcwd()],
    binaries=binaries,  # Include binaries
    datas=datas,  # Include data files
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    cipher=block_cipher,
    noarchive=False,
)

# Build Python archive (PYZ)
pyz = PYZ(a.pure)

# Create executable (EXE)
exe = EXE(
    pyz,
    a.scripts,  # Main scripts to bundle
    a.binaries,  # Include binaries
    exclude_binaries=True,  # Exclude binaries from the EXE (handled by COLLECT)
    name='app',  # Name of the executable
    debug=False,  # No debug mode
    bootloader_ignore_signals=False,
    strip=False,  # Don't strip debug information
    upx=True,  # Use UPX compression
    console=False,  # Console application
    disable_windowed_traceback=False,  # Enable traceback in the console
    argv_emulation=False,  # No argument emulation
    target_arch=None,  # No specific architecture target
    codesign_identity=None,  # No code signing
    entitlements_file=None,  # No entitlement file
)

# Collect everything into the final executable directory
coll = COLLECT(
    exe,
    a.binaries,  # Include binaries
    a.datas,  # Include data files
    strip=False,  # Don't strip files
    upx=True,  # Use UPX compression
    upx_exclude=[],  # No exclusions from UPX
    name='app',  # Name of the final app
)
