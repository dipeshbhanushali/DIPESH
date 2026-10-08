; Inno Setup script: turns dist\DIPESH\ into a Windows installer.
;
;   1. pyinstaller build\dipesh.spec --noconfirm --clean
;   2. Inno Setup (free): https://jrsoftware.org/isdl.php
;   3. iscc build\installer.iss
;
; Produces installer\DIPESH-setup-1.0.0.exe: Start Menu entry, optional
; desktop icon, uninstaller, no admin rights needed.

#define AppName     "DIPESH"
#define AppVersion  "1.0.0"
#define AppExe      "DIPESH.exe"

[Setup]
AppId={{6C0A8E5D-2B41-4F7A-9D36-D1E5A7C3B902}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Dipesh Bhanushali
DefaultDirName={autopf}\DIPESH
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\installer
OutputBaseFilename=DIPESH-setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\DIPESH\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Start {#AppName}"; Flags: nowait postinstall skipifsilent
