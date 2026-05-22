@echo off
echo ============================================
echo  Soup Macro - Build
echo ============================================
echo.

echo [1/5] Installiere Abhaengigkeiten...
pip install pynput pyinstaller pillow pystray
echo.

echo [2/5] Erstelle Icon aus logo.png...
python make_icon.py
echo.

echo [3/5] Erstelle .exe mit PyInstaller (1-2 Minuten)...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist
if exist SoupMacro.spec del SoupMacro.spec
pyinstaller --clean --onefile --windowed ^
  --name "SoupMacro" ^
  --icon=logo.ico ^
  --add-data "logo.png;." ^
  --uac-admin ^
  macro_tool.py
echo.

echo [4/5] Suche Inno Setup...

:: 1) Versuche ISCC direkt aus PATH
set ISCC=
where ISCC.exe >nul 2>&1
if %errorlevel% == 0 (
  set ISCC=ISCC.exe
  goto :build_installer
)

:: 2) Bekannte Installationspfade durchsuchen
for %%P in (
  "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
  "%ProgramFiles%\Inno Setup 6\ISCC.exe"
  "%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe"
  "%ProgramFiles%\Inno Setup 5\ISCC.exe"
  "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
  "%LocalAppData%\Programs\Inno Setup 5\ISCC.exe"
  "C:\InnoSetup\ISCC.exe"
  "C:\Tools\InnoSetup\ISCC.exe"
) do (
  if exist %%P (
    set ISCC=%%P
    goto :build_installer
  )
)

:: 3) Registry abfragen (Inno Setup 6)
for /f "tokens=2*" %%A in (
  'reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1" /v "InstallLocation" 2^>nul'
) do (
  if exist "%%B\ISCC.exe" (
    set ISCC="%%B\ISCC.exe"
    goto :build_installer
  )
)
for /f "tokens=2*" %%A in (
  'reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1" /v "InstallLocation" 2^>nul'
) do (
  if exist "%%B\ISCC.exe" (
    set ISCC="%%B\ISCC.exe"
    goto :build_installer
  )
)

:: 4) Nicht gefunden
echo.
echo  WARNUNG: Inno Setup wurde nicht gefunden!
echo  Bitte Installationspfad manuell eintragen:
echo.
set /p ISCC_MANUAL="  Pfad zu ISCC.exe: "
if exist "%ISCC_MANUAL%" (
  set ISCC="%ISCC_MANUAL%"
  goto :build_installer
)
echo  Ungültiger Pfad – Installer wird übersprungen.
goto :done

:build_installer
echo  Gefunden: %ISCC%
echo.
%ISCC% setup.iss
if %errorlevel% == 0 (
  goto :success
) else (
  echo  FEHLER beim Erstellen des Installers!
  goto :done
)

:success
echo.
echo ============================================
echo  BUILD ERFOLGREICH!
echo ============================================
echo  Installer: Output\SoupMacro_Setup.exe    ^<-- fuer GitHub Release
echo  Raw .exe:  dist\SoupMacro.exe
echo ============================================
goto :done

:done
echo.
pause
