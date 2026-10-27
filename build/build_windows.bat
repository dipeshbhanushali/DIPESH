@echo off
REM Build DIPESH and its installer. Run from the repository root, in cmd:
REM     build\build_windows.bat
REM
REM   dist\DIPESH\DIPESH.exe                   the app (portable folder)
REM   installer\DIPESH-setup-2.0.0.exe           if Inno Setup is installed

setlocal
echo [1/4] Clean build environment...
python -m venv .buildenv                         || goto :error
call .buildenv\Scripts\activate.bat              || goto :error

echo [2/4] Installing...
python -m pip install --upgrade pip              || goto :error
python -m pip install .                          || goto :error
python -m pip install pyinstaller                || goto :error

echo [3/4] Building...
pyinstaller build\dipesh.spec --noconfirm --clean || goto :error

echo [4/4] Installer...
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    %ISCC% build\installer.iss                   || goto :error
    echo Installer: installer\DIPESH-setup-2.0.0.exe
) else (
    echo Inno Setup not found - skipped. The app is in dist\DIPESH\
)
echo.
echo First launch of an unsigned program shows a SmartScreen warning:
echo "More info" -^> "Run anyway".
goto :eof

:error
echo BUILD FAILED at the step above.
exit /b 1
