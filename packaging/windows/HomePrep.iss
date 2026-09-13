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

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--install-service"; Flags: runhidden waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Parameters: "--start-service"; Flags: runhidden waituntilterminated
Filename: "http://127.0.0.1:8080"; Description: "Open HomePrep"; Flags: shellexec nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--stop-service"; Flags: runhidden waituntilterminated; RunOnceId: "StopHomePrepService"
Filename: "{app}\{#MyAppExeName}"; Parameters: "--remove-service"; Flags: runhidden waituntilterminated; RunOnceId: "RemoveHomePrepService"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  { Stop either the new service or a legacy foreground/autostart process before upgrade. }
  Exec(ExpandConstant('{sys}\sc.exe'), 'stop HomePrepServer', '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM HomePrepServer.exe /F', '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode);

  { Older installer builds used HKLM Run instead of a Windows service. }
  RegDeleteValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Run', 'HomePrepServer');
  Result := '';
end;

{ Preparedness data intentionally lives outside the installation directory
  under %ProgramData%\HomePrep and is not removed during uninstall. }
