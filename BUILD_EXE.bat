@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  Biyik.dev - Exe derleme (gelistirme)
echo  BYK Seri Baskı Pro
echo ========================================
echo.
echo Dagitim / tek tik kurulum icin BUILD_RELEASE.bat kullanin.
echo.

python -m pip install -r requirements.txt pyinstaller -q
if errorlevel 1 (
  echo pip hatasi.
  pause
  exit /b 1
)

echo Ikonlar hazirlaniyor (app.ico / iconset)...
python tools\prepare_icons.py
if errorlevel 1 (
  echo Ikon hazirlama uyarisi — mevcut assets kullanilacak.
)

echo PyInstaller calisiyor...
python -m PyInstaller --noconfirm BYKSeriBaskiPro.spec
if errorlevel 1 (
  echo Derleme basarisiz.
  pause
  exit /b 1
)

echo.
echo Cikti: dist\BYKSeriBaskiPro\
echo Yerel kurulum: KURULUM.bat
echo Paylasim paketi: BUILD_RELEASE.bat
echo.
pause
