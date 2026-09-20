@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  BYK Seri Baskı Pro - Kurulum
echo  Biyik.dev
echo ========================================
echo.

if exist "%~dp0BYKSeriBaskiPro_Kurulum.exe" (
  start "" "%~dp0BYKSeriBaskiPro_Kurulum.exe"
  exit /b 0
)

set "SRC="
if exist "%~dp0dist\BYKSeriBaskiPro\BYKSeriBaskiPro.exe" (
  set "SRC=%~dp0dist\BYKSeriBaskiPro"
)
if exist "%~dp0BYKSeriBaskiPro\BYKSeriBaskiPro.exe" (
  set "SRC=%~dp0BYKSeriBaskiPro"
)

if "%SRC%"=="" (
  echo Kurulum kaynagi bulunamadi.
  echo.
  echo Secenekler:
  echo  - BUILD_RELEASE.bat ile Kurulum.exe uretin
  echo  - veya once BUILD_EXE.bat calistirin
  pause
  exit /b 1
)

set "DEST=%LOCALAPPDATA%\BiyikDev\BYKSeriBaskiPro"
echo Kaynak: %SRC%
echo Hedef : %DEST%
echo.

if not exist "%DEST%" mkdir "%DEST%"
xcopy "%SRC%\*" "%DEST%\" /E /I /Y /Q >nul
if errorlevel 1 (
  echo Dosya kopyalama hatasi.
  pause
  exit /b 1
)

set "MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Biyik.dev"
if not exist "%MENU%" mkdir "%MENU%"

set "ICON=%DEST%\app.ico"
if not exist "%ICON%" if exist "%DEST%\_internal\assets\app.ico" (
  copy /Y "%DEST%\_internal\assets\app.ico" "%DEST%\app.ico" >nul
)
if not exist "%ICON%" if exist "%DEST%\assets\app.ico" (
  copy /Y "%DEST%\assets\app.ico" "%DEST%\app.ico" >nul
)
if not exist "%ICON%" set "ICON=%DEST%\BYKSeriBaskiPro.exe,0"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%MENU%\BYK Seri Baskı Pro.lnk'); $s.TargetPath = '%DEST%\BYKSeriBaskiPro.exe'; $s.WorkingDirectory = '%DEST%'; $s.IconLocation = '%ICON%'; $s.Description = 'BYK Seri Baskı Pro — Biyik.dev'; $s.Save()"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $desk = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut((Join-Path $desk 'BYK Seri Baskı Pro.lnk')); $s.TargetPath = '%DEST%\BYKSeriBaskiPro.exe'; $s.WorkingDirectory = '%DEST%'; $s.IconLocation = '%ICON%'; $s.Save()"

(
echo @echo off
echo chcp 65001 ^>nul
echo setlocal
echo set "DEST=%%LOCALAPPDATA%%\BiyikDev\BYKSeriBaskiPro"
echo set "MENU=%%APPDATA%%\Microsoft\Windows\Start Menu\Programs\Biyik.dev"
echo set "DESK=%%USERPROFILE%%\Desktop\BYK Seri Baskı Pro.lnk"
echo echo Kaldiriliyor...
echo taskkill /IM BYKSeriBaskiPro.exe /F ^>nul 2^>^&1
echo if exist "%%MENU%%\BYK Seri Baskı Pro.lnk" del /f /q "%%MENU%%\BYK Seri Baskı Pro.lnk"
echo if exist "%%DESK%%" del /f /q "%%DESK%%"
echo if exist "%%MENU%%" rd "%%MENU%%" 2^>nul
echo cd /d "%%TEMP%%"
echo if exist "%%DEST%%" rd /s /q "%%DEST%%"
echo echo Kaldirma tamamlandi.
echo pause
) > "%DEST%\KALDIR.bat"

echo.
echo Kurulum tamamlandi.
echo Klasor: %DEST%
echo.
set /p RUN="Simdi uygulamayi acmak ister misiniz? (E/H): "
if /i "%RUN%"=="E" start "" "%DEST%\BYKSeriBaskiPro.exe"

endlocal
pause
