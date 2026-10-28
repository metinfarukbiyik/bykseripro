@echo off
chcp 65001 >nul
setlocal

set "DEST=%LOCALAPPDATA%\BiyikDev\BYKSeriBaskiPro"
set "OLDDEST=%LOCALAPPDATA%\BiyikDev\SeriBarkodEtiketBaski"
set "MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Biyik.dev"
set "DESK=%USERPROFILE%\Desktop\BYK Seri Baskı Pro.lnk"
set "OLDDESK=%USERPROFILE%\Desktop\Seri Barkod Etiket Baski.lnk"

echo BYK Seri Baskı Pro kaldiriliyor...
taskkill /IM BYKSeriBaskiPro.exe /F >nul 2>&1
taskkill /IM SeriBarkodEtiketBaski.exe /F >nul 2>&1

if exist "%MENU%\BYK Seri Baskı Pro.lnk" del /f /q "%MENU%\BYK Seri Baskı Pro.lnk"
if exist "%MENU%\Seri Barkod Etiket Baski.lnk" del /f /q "%MENU%\Seri Barkod Etiket Baski.lnk"
if exist "%DESK%" del /f /q "%DESK%"
if exist "%OLDDESK%" del /f /q "%OLDDESK%"
if exist "%MENU%" rd "%MENU%" 2>nul

cd /d "%TEMP%"
if exist "%DEST%" (
  rd /s /q "%DEST%"
  echo Dosyalar silindi: %DEST%
)
if exist "%OLDDEST%" (
  rd /s /q "%OLDDEST%"
  echo Eski kurulum silindi: %OLDDEST%
)
if not exist "%DEST%" if not exist "%OLDDEST%" (
  echo Kurulum klasoru bulunamadi.
)

echo Kaldirma tamamlandi.
pause
endlocal
