@echo off
echo ========================================
echo Building Warframe Relic Companion
echo ========================================
echo.

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Building EXE...
pyinstaller "Warframe Relic Companion.spec" --noconfirm

echo.
echo Copying DB folder with data...
if exist "dist\DB" rmdir /s /q "dist\DB"
xcopy "DB" "dist\DB" /E /I /Y

echo Copying icons folder...
if exist "dist\icons" rmdir /s /q "dist\icons"
xcopy "icons" "dist\icons" /E /I /Y

echo.
echo ========================================
echo Build complete!
echo EXE is in: dist\Warframe Relic Companion.exe
echo ========================================
pause
