"""
GitHub Auto-Updater for The Relic Vault.
Checks for updates from GitHub releases and handles the update process.
Supports both Python script and compiled exe versions.
"""

import os
import sys
import json
import shutil
import zipfile
import tempfile
import threading
import subprocess
from typing import Optional, Callable
from dataclasses import dataclass

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False


# Current version - increment this with each release
__version__ = "1.1.8"

# GitHub repository info
GITHUB_OWNER = "RelicRush"
GITHUB_REPO = "RelicCompanion"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


def is_frozen() -> bool:
    """Check if running as a compiled exe (PyInstaller, cx_Freeze, etc.)."""
    return getattr(sys, 'frozen', False)


def get_exe_path() -> str:
    """Get the path to the current executable."""
    if is_frozen():
        return sys.executable
    return None


@dataclass
class UpdateInfo:
    """Information about an available update."""
    current_version: str
    latest_version: str
    update_available: bool
    download_url: Optional[str] = None
    exe_download_url: Optional[str] = None
    release_notes: Optional[str] = None
    release_name: Optional[str] = None
    error: Optional[str] = None


def get_version() -> str:
    """Get the current application version."""
    return __version__


def parse_version(version_str: str) -> tuple:
    """Parse a version string into a comparable tuple."""
    # Remove 'v' prefix if present
    version_str = version_str.lstrip('v').strip()
    
    # Split by dots and convert to integers
    try:
        parts = version_str.split('.')
        return tuple(int(p) for p in parts)
    except (ValueError, AttributeError):
        return (0, 0, 0)


def is_newer_version(latest: str, current: str) -> bool:
    """Check if latest version is newer than current."""
    return parse_version(latest) > parse_version(current)


def check_for_updates() -> UpdateInfo:
    """
    Check GitHub for available updates.
    
    Returns:
        UpdateInfo with update details
    """
    current = __version__
    
    try:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "WarframeRelicCompanion-Updater"
        }
        
        if HAS_REQUESTS:
            response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
        else:
            request = urllib.request.Request(GITHUB_API_URL, headers=headers)
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode())
        
        latest_version = data.get("tag_name", "0.0.0")
        release_name = data.get("name", "")
        release_notes = data.get("body", "")
        
        # Find download URLs
        download_url = None
        exe_download_url = None
        
        for asset in data.get("assets", []):
            asset_name = asset.get("name", "").lower()
            browser_url = asset.get("browser_download_url")
            
            # Look for EXE file
            if asset_name.endswith(".exe"):
                exe_download_url = browser_url
            # Look for ZIP file
            elif asset_name.endswith(".zip"):
                download_url = browser_url
        
        # Fallback to source zip if no assets
        if not download_url and not exe_download_url:
            download_url = data.get("zipball_url")
        
        update_available = is_newer_version(latest_version, current)
        
        return UpdateInfo(
            current_version=current,
            latest_version=latest_version,
            update_available=update_available,
            download_url=download_url,
            exe_download_url=exe_download_url,
            release_notes=release_notes,
            release_name=release_name
        )
        
    except Exception as e:
        return UpdateInfo(
            current_version=current,
            latest_version="Unknown",
            update_available=False,
            error=str(e)
        )


def check_for_updates_async(callback: Callable[[UpdateInfo], None]):
    """
    Check for updates in a background thread.
    
    Args:
        callback: Function to call with UpdateInfo result
    """
    def do_check():
        result = check_for_updates()
        callback(result)
    
    thread = threading.Thread(target=do_check, daemon=True)
    thread.start()


def download_update(download_url: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> Optional[str]:
    """
    Download an update to a temporary file.
    
    Args:
        download_url: URL to download from
        progress_callback: Optional callback(downloaded_bytes, total_bytes)
        
    Returns:
        Path to downloaded file, or None on failure
    """
    try:
        temp_dir = tempfile.mkdtemp(prefix="wfrc_update_")
        temp_file = os.path.join(temp_dir, "update.zip")
        
        if HAS_REQUESTS:
            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)
        else:
            request = urllib.request.Request(download_url)
            with urllib.request.urlopen(request, timeout=60) as response:
                with open(temp_file, 'wb') as f:
                    shutil.copyfileobj(response, f)
        
        return temp_file
        
    except Exception as e:
        print(f"Download error: {e}")
        return None


def get_app_directory() -> str:
    """Get the application's installation directory."""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))


def apply_update(zip_path: str, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
    """
    Apply an update from a downloaded zip file.
    
    Args:
        zip_path: Path to the update zip file
        progress_callback: Optional callback for status messages
        
    Returns:
        True if successful, False otherwise
    """
    try:
        app_dir = get_app_directory()
        
        if progress_callback:
            progress_callback("Extracting update...")
        
        # Create a backup
        backup_dir = os.path.join(tempfile.gettempdir(), "wfrc_backup")
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        
        if progress_callback:
            progress_callback("Creating backup...")
        
        # Extract to temp location first
        extract_dir = tempfile.mkdtemp(prefix="wfrc_extract_")
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
        
        # Find the actual content directory (GitHub zips have a folder inside)
        contents = os.listdir(extract_dir)
        if len(contents) == 1 and os.path.isdir(os.path.join(extract_dir, contents[0])):
            source_dir = os.path.join(extract_dir, contents[0])
        else:
            source_dir = extract_dir
        
        if progress_callback:
            progress_callback("Applying update...")
        
        # Copy new files, preserving user data
        preserve_files = ['settings.json', 'relic_companion.db', 'wfcd_relics.db']
        preserve_dirs = ['DB', 'icons']
        
        for item in os.listdir(source_dir):
            src = os.path.join(source_dir, item)
            dst = os.path.join(app_dir, item)
            
            # Skip preserved items
            if item in preserve_files or item in preserve_dirs:
                continue
            
            if os.path.isfile(src):
                if src.endswith('.py') or src.endswith('.spec'):
                    shutil.copy2(src, dst)
            elif os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
        
        # Cleanup
        if progress_callback:
            progress_callback("Cleaning up...")
        
        shutil.rmtree(extract_dir, ignore_errors=True)
        os.remove(zip_path)
        
        if progress_callback:
            progress_callback("Update complete! Please restart the application.")
        
        return True
        
    except Exception as e:
        print(f"Update error: {e}")
        if progress_callback:
            progress_callback(f"Update failed: {e}")
        return False


def download_exe_update(download_url: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> Optional[str]:
    """
    Download a new EXE to a temporary location.
    
    Args:
        download_url: URL to download from
        progress_callback: Optional callback(downloaded_bytes, total_bytes)
        
    Returns:
        Path to downloaded EXE, or None on failure
    """
    try:
        # Create temp directory that persists after app closes
        temp_dir = os.path.join(tempfile.gettempdir(), "wfrc_update")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        temp_exe = os.path.join(temp_dir, "TheRelicVault_new.exe")
        
        headers = {"User-Agent": "TheRelicVault-Updater"}
        
        if HAS_REQUESTS:
            response = requests.get(download_url, headers=headers, stream=True, timeout=120)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(temp_exe, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)
        else:
            request = urllib.request.Request(download_url, headers=headers)
            with urllib.request.urlopen(request, timeout=120) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                with open(temp_exe, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)
        
        return temp_exe
        
    except Exception as e:
        print(f"Download error: {e}")
        return None


def create_update_script(new_exe_path: str, current_exe_path: str) -> str:
    """
    Create a batch script that will replace the EXE after the app closes.
    
    Args:
        new_exe_path: Path to the downloaded new EXE
        current_exe_path: Path to the current running EXE
        
    Returns:
        Path to the batch script
    """
    script_dir = os.path.join(tempfile.gettempdir(), "wfrc_update")
    os.makedirs(script_dir, exist_ok=True)
    script_path = os.path.join(script_dir, "update.bat")
    
    exe_name = os.path.basename(current_exe_path)
    new_exe_size = os.path.getsize(new_exe_path) if os.path.exists(new_exe_path) else 0
    
    # Batch script that waits for app to close, replaces EXE, restarts
    script_content = f'''@echo off
setlocal enabledelayedexpansion
echo ============================================
echo   Updating The Relic Vault...
echo ============================================
echo.

:: Wait for the app to close
echo Waiting for application to close...
set /a count=0
:waitloop
tasklist /FI "IMAGENAME eq {exe_name}" 2>NUL | find /I "{exe_name}" >NUL
if "!ERRORLEVEL!"=="0" (
    set /a count+=1
    if !count! GEQ 60 (
        echo ERROR: Timeout waiting for app to close.
        echo Please close the application manually and try again.
        pause
        exit /b 1
    )
    timeout /t 1 /nobreak >NUL
    goto waitloop
)
echo Application closed.

:: Extra delay for file handles to be released
echo Waiting for file handles to release...
timeout /t 3 /nobreak >NUL

:: Backup old EXE
echo Creating backup...
if exist "{current_exe_path}.backup" del /f /q "{current_exe_path}.backup" >NUL 2>&1
if exist "{current_exe_path}" (
    move /y "{current_exe_path}" "{current_exe_path}.backup" >NUL 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo ERROR: Could not backup old EXE. File may be in use.
        pause
        exit /b 1
    )
)
echo Backup created.

:: Copy new EXE using xcopy for better reliability
echo Installing update...
xcopy /y /q "{new_exe_path}" "{current_exe_path}*" >NUL 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Update failed during copy!
    echo Restoring backup...
    if exist "{current_exe_path}.backup" (
        move /y "{current_exe_path}.backup" "{current_exe_path}" >NUL 2>&1
    )
    pause
    exit /b 1
)

:: Verify the copy by checking file size
for %%A in ("{current_exe_path}") do set "newsize=%%~zA"
if !newsize! LSS {max(new_exe_size - 1000, 1)} (
    echo ERROR: Update file appears corrupted!
    echo Restoring backup...
    del /f /q "{current_exe_path}" >NUL 2>&1
    if exist "{current_exe_path}.backup" (
        move /y "{current_exe_path}.backup" "{current_exe_path}" >NUL 2>&1
    )
    pause
    exit /b 1
)

echo Update installed successfully!

:: Clean up backup
del /f /q "{current_exe_path}.backup" >NUL 2>&1

:: Small delay before launching
timeout /t 2 /nobreak >NUL

echo Starting The Relic Vault...
start "" "{current_exe_path}"

:: Clean up update files after a delay
timeout /t 5 /nobreak >NUL
rmdir /s /q "{script_dir}" >NUL 2>&1

exit
'''
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    return script_path


def apply_exe_update(new_exe_path: str) -> tuple[bool, str]:
    """
    Apply an EXE update by creating an update script and launching it.
    The script will replace the EXE after the app closes.
    
    Args:
        new_exe_path: Path to the downloaded new EXE
        
    Returns:
        Tuple of (success, error_message)
    """
    if not is_frozen():
        return False, "Auto-update only works for compiled EXE versions"
    
    current_exe = get_exe_path()
    if not current_exe:
        return False, "Could not determine current EXE path"
    
    if not os.path.exists(new_exe_path):
        return False, f"Downloaded EXE not found: {new_exe_path}"
    
    try:
        # Create the update script
        script_path = create_update_script(new_exe_path, current_exe)
        
        if not os.path.exists(script_path):
            return False, "Failed to create update script"
        
        # Launch the script detached from this process
        # Use CREATE_NO_WINDOW to hide the console, and DETACHED_PROCESS so it survives app exit
        subprocess.Popen(
            f'cmd /c "{script_path}"',
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            close_fds=True
        )
        
        return True, ""
        
    except Exception as e:
        return False, f"Failed to launch update script: {e}"


def download_and_apply_update(update_info: UpdateInfo, 
                               progress_callback: Optional[Callable[[str, int, int], None]] = None,
                               complete_callback: Optional[Callable[[bool, str], None]] = None):
    """
    Download and apply an update in a background thread.
    
    Args:
        update_info: UpdateInfo with download URL
        progress_callback: Called with (status_text, downloaded_bytes, total_bytes)
        complete_callback: Called with (success, message) when done
    """
    def do_update():
        try:
            # Determine which URL to use
            if is_frozen() and update_info.exe_download_url:
                download_url = update_info.exe_download_url
            elif update_info.download_url:
                download_url = update_info.download_url
            else:
                if complete_callback:
                    complete_callback(False, "No download URL available")
                return
            
            # Download progress wrapper
            def on_progress(downloaded, total):
                if progress_callback:
                    mb_downloaded = downloaded / (1024 * 1024)
                    mb_total = total / (1024 * 1024) if total > 0 else 0
                    status = f"Downloading... {mb_downloaded:.1f} / {mb_total:.1f} MB"
                    progress_callback(status, downloaded, total)
            
            if progress_callback:
                progress_callback("Starting download...", 0, 0)
            
            # Download the update
            if is_frozen() and update_info.exe_download_url:
                new_exe = download_exe_update(download_url, on_progress)
                
                if not new_exe:
                    if complete_callback:
                        complete_callback(False, "Download failed")
                    return
                
                if progress_callback:
                    progress_callback("Preparing update...", 100, 100)
                
                # Apply the update
                success, error_msg = apply_exe_update(new_exe)
                if success:
                    if complete_callback:
                        complete_callback(True, "Update ready! The app will now close and update.")
                else:
                    if complete_callback:
                        complete_callback(False, f"Failed to prepare update: {error_msg}")
            else:
                # For non-EXE versions, just open the download page
                import webbrowser
                webbrowser.open(GITHUB_RELEASES_URL)
                if complete_callback:
                    complete_callback(True, "Opening download page in browser...")
                    
        except Exception as e:
            if complete_callback:
                complete_callback(False, f"Update error: {e}")
    
    thread = threading.Thread(target=do_update, daemon=True)
    thread.start()


# Quick test
if __name__ == "__main__":
    print(f"Current version: {__version__}")
    print(f"Running as EXE: {is_frozen()}")
    print("Checking for updates...")
    
    info = check_for_updates()
    print(f"Latest version: {info.latest_version}")
    print(f"Update available: {info.update_available}")
    print(f"EXE download URL: {info.exe_download_url}")
    if info.error:
        print(f"Error: {info.error}")
    if info.release_notes:
        print(f"Release notes:\n{info.release_notes[:200]}...")
