#define MyAppName "HomePrep Server"
#define MyAppVersion "0.1.0-dev0"
#define MyAppPublisher "HomePrep"
#define MyAppExeName "HomePrepServer.exe"

[Setup]
AppId={{7A5E0C9F-26F9-4E7C-A649-AD5E79429311}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\HomePrep
DefaultGroupName=HomePrep
DisableProgramGroupPage=yes
OutputDir=..\..\dist\installer
OutputBaseFilename=HomePrep-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\..\dist\HomePrepServer.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{commonappdata}\HomePrep"; Permissions: users-modify

[Icons]
Name: "{autoprograms}\HomePrep"; Filename: "http://127.0.0.1:8080"
Name: "{autodesktop}\HomePrep"; Filename: "http://127.0.0.1:8080"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Registry]
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "HomePrepServer"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--open-browser"; Description: "Start HomePrep"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /IM {#MyAppExeName} /F"; Flags: runhidden; RunOnceId: "StopHomePrep"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

; Preparedness data intentionally lives outside the installation directory
; under %ProgramData%\HomePrep and is not removed during uninstall.
