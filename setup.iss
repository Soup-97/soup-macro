; ============================================================
;  Soup Macro â€“ Inno Setup Script
;  Requires: Inno Setup 6  (https://jrsoftware.org/isdl.php)
; ============================================================

#define AppName      "Soup Macro"
#define AppVersion   "1.6"
#define AppPublisher "FunkelVult"
#define AppURL       "https://github.com/FunkelVult/soup-macro"
#define AppExe       "SoupMacro.exe"

[Setup]
AppId={{B7E2A1C4-3F8D-4E92-BC56-A1234567890F}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}

; Install to Program Files\Soup Macro
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}

; Output
OutputDir=Output
OutputBaseFilename=SoupMacro_Setup
SetupIconFile=logo.ico

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
InternalCompressLevel=ultra64

; UI
WizardStyle=modern
WizardSizePercent=100
DisableWelcomePage=no
LicenseFile=

; Privileges
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Misc
AllowNoIcons=yes
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Installer
ArchitecturesInstallIn64BitMode=x64compatible

; Automatically close the app if it's running during install/update
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartApplications=yes

[Languages]
Name: "german";  MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; \
  Description: "{cm:CreateDesktopIcon}"; \
  GroupDescription: "{cm:AdditionalIcons}"; \
  Flags: unchecked
Name: "startupicon"; \
  Description: "Soup Macro automatisch mit Windows starten"; \
  GroupDescription: "Autostart:"; \
  Flags: unchecked

[Files]
; Main executable (built by PyInstaller --onefile)
Source: "dist\{#AppExe}"; \
  DestDir: "{app}"; \
  Flags: ignoreversion

[Icons]
; Start menu
Name: "{group}\{#AppName}";              Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} deinstallieren"; Filename: "{uninstallexe}"

; Desktop shortcut (optional)
Name: "{commondesktop}\{#AppName}"; \
  Filename: "{app}\{#AppExe}"; \
  Tasks: desktopicon

[Registry]
; Autostart (optional task)
Root: HKCU; \
  Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; \
  ValueName: "SoupMacro"; \
  ValueData: """{app}\{#AppExe}"""; \
  Flags: uninsdeletevalue; \
  Tasks: startupicon

[Run]
; Launch after install
Filename: "{app}\{#AppExe}"; \
  Description: "{#AppName} jetzt starten"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up the install folder completely
Type: filesandordirs; Name: "{app}"
