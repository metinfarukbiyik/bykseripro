@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  BIYIK.DEV - Surum / Kurulum paketi
echo  BYK Seri Baskı Pro
echo ========================================
echo.

set "VER=1.1.1"
if exist VERSION (
  set /p VER=<VERSION
)

echo [1/5] Bagimliliklar...
python -m pip install -r requirements.txt pyinstaller -q
if errorlevel 1 (
  echo pip hatasi.
  pause
  exit /b 1
)

echo [1b] Ikonlar (app.ico / iconset)...
python tools\prepare_icons.py
if errorlevel 1 (
  echo Ikon hazirlama uyarisi — mevcut assets kullanilacak.
)

echo [2/5] Uygulama derleniyor (PyInstaller)...
python -m PyInstaller --noconfirm BYKSeriBaskiPro.spec
if errorlevel 1 (
  echo Uygulama derlemesi basarisiz.
  pause
  exit /b 1
)

if not exist "dist\BYKSeriBaskiPro\BYKSeriBaskiPro.exe" (
  echo dist klasoru bulunamadi.
  pause
  exit /b 1
)

echo [3/5] payload.zip olusturuluyor...
if exist payload.zip del /f /q payload.zip
powershell -NoProfile -Command ^
  "Compress-Archive -Path 'dist\BYKSeriBaskiPro\*' -DestinationPath 'payload.zip' -Force"
if not exist payload.zip (
  echo payload.zip olusturulamadi.
  pause
  exit /b 1
)

echo [4/5] Kurulum.exe derleniyor...
python -m PyInstaller --noconfirm Kurulum.spec
if errorlevel 1 (
  echo Kurulum.exe derlemesi basarisiz.
  pause
  exit /b 1
)

echo [5/5] release klasoru hazirlaniyor...
set "OUT=release\BYKSeriBaskiPro_v%VER%_Kurulum"
if exist "release" rd /s /q "release" 2>nul
mkdir "release" 2>nul
mkdir "%OUT%" 2>nul

copy /Y "dist\BYKSeriBaskiPro_Kurulum.exe" "%OUT%\BYKSeriBaskiPro_Kurulum.exe" >nul
copy /Y "DAGITIM.txt" "%OUT%\OKU_BENI.txt" >nul
copy /Y "VERSION" "%OUT%\VERSION.txt" >nul

powershell -NoProfile -Command ^
  "Compress-Archive -Path 'dist\BYKSeriBaskiPro\*' -DestinationPath 'release\BYKSeriBaskiPro_v%VER%_Portable.zip' -Force"

powershell -NoProfile -Command ^
  "Compress-Archive -Path '%OUT%\*' -DestinationPath 'release\BYKSeriBaskiPro_v%VER%_Kurulum.zip' -Force"

echo.
echo ========================================
echo  TAMAM
echo ========================================
echo.
echo Paylasilacak dosya (onerilen):
echo   release\BYKSeriBaskiPro_v%VER%_Kurulum.zip
echo.
echo  Icinde:
echo   BYKSeriBaskiPro_Kurulum.exe  - cift tikla kur
echo   OKU_BENI.txt
echo.
echo Alternatif (kurulumsuz):
echo   release\BYKSeriBaskiPro_v%VER%_Portable.zip
echo.
echo Alici: zip'i acip Kurulum.exe'ye cift tiklar. Python gerekmez.
echo.
pause
endlocal
