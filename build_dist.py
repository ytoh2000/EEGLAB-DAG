import os
import sys
import platform
import shutil
import subprocess

def clean_build_dirs():
    """Remove build and dist directories if they exist."""
    for d in ['build', 'dist']:
        if os.path.exists(d):
            shutil.rmtree(d)

def get_os_key():
    """Return the OS key for the bin directory (win64, maca64, linux64)."""
    system = platform.system().lower()
    if system == 'windows':
        return 'win64'
    elif system == 'darwin':
        return 'maca64'
    elif system == 'linux':
        return 'linux64'
    else:
        raise ValueError(f"Unsupported OS: {system}")

def build():
    clean_build_dirs()
    
    os_key = get_os_key()
    output_dir = os.path.join('bin', os_key)
    
    # Ensure output directory exists (and clean it)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    # PyInstaller arguments
    args = [
        'src/main.py',              # Entry point
        '--name=main',              # Name of the executable
        '--noconfirm',              # Replace output directory without asking
        '--onedir',                 # Create a directory with executable and libs
        '--windowed',               # Do not open a console window (for GUI)
        '--clean',                  # Clean PyInstaller cache
        '--hidden-import=PyQt6',
        '--hidden-import=networkx',
        '--distpath', output_dir    # Output to bin/<os_key>
    ]
    
    # Add data files if needed (e.g., icons)
    # args.append('--add-data=src/gui/icons:src/gui/icons') # Example
    
    print(f"Building for {os_key}...")
    print(f"Command: pyinstaller {' '.join(args)}")
    
    # Run PyInstaller
    subprocess.check_call(['pyinstaller'] + args)
    
    # Library is now external (in root/library/nodes), so we don't copy it into dist.
    
    print(f"Build complete. Output in {output_dir}")

if __name__ == '__main__':
    # Check if PyInstaller is installed
    if shutil.which('pyinstaller') is None:
        print("Error: PyInstaller is not installed. Run 'pip install pyinstaller'.")
        sys.exit(1)
        
    build()
