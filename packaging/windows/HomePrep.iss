#define MyAppName "HomePrep Server"
#define MyAppVersion "0.1.0-dev0"
#define MyAppVersionInfo "0.1.0.0"
#define MyAppPublisher "HomePrep"
#define MyAppURL "https://github.com/kakelakel/homeprep-server"
#define MyAppExeName "HomePrepServer.exe"
#define MyManagerExeName "HomePrepServerManager.exe"

[Setup]
AppId={{7A5E0C9F-26F9-4E7C-A649-AD5E79429311}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
VersionInfoVersion={#MyAppVersionInfo}
VersionInfoProductName={#MyAppName}
VersionInfoDescription=Self-hosted HomePrep Server and Web application
DefaultDirName={autopf}\HomePrep
DefaultGroupName=HomePrep
DisableProgramGroupPage=yes
DisableWelcomePage=no
OutputDir=..\..\dist\installer
OutputBaseFilename=HomePrep-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
SetupLogging=yes
ShowLanguageDialog=no

[Files]
; Both executables are self-contained PyInstaller builds. End users do not need
; Python, Node.js, npm, .NET, Visual C++ redistributables or a separate Web runtime.
Source: "..\..\dist\HomePrepServer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\HomePrepServerManager.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Preparedness data intentionally lives outside Program Files so upgrades and
; uninstall/reinstall operations do not destroy the household database/backups.
Name: "{commonappdata}\HomePrep"; Permissions: users-modify
Name: "{commonappdata}\HomePrep\backups"; Permissions: users-modify

[Icons]
Name: "{autoprograms}\HomePrep"; Filename: "{app}\{#MyManagerExeName}"; Parameters: "--open-homeprep"
Name: "{autoprograms}\HomePrep Server Manager"; Filename: "{app}\{#MyManagerExeName}"
Name: "{autodesktop}\HomePrep"; Filename: "{app}\{#MyManagerExeName}"; Parameters: "--open-homeprep"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--install-service"; StatusMsg: "Installing HomePrep Server service…"; Flags: runhidden waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Parameters: "--start-service"; StatusMsg: "Starting HomePrep Server…"; Flags: runhidden waituntilterminated
Filename: "{app}\{#MyManagerExeName}"; Parameters: "--open-homeprep"; Description: "Open HomePrep"; Flags: nowait postinstall skipifsilent runasoriginaluser
Filename: "{app}\{#MyManagerExeName}"; Description: "Open HomePrep Server Manager"; Flags: nowait postinstall skipifsilent runasoriginaluser unchecked

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--stop-service"; Flags: runhidden waituntilterminated; RunOnceId: "StopHomePrepService"
Filename: "{app}\{#MyAppExeName}"; Parameters: "--remove-service"; Flags: runhidden waituntilterminated; RunOnceId: "RemoveHomePrepService"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
procedure InitializeWizard;
var
  InfoLabel: TNewStaticText;
begin
  InfoLabel := TNewStaticText.Create(WizardForm);
  InfoLabel.Parent := WizardForm.SelectDirPage;
  InfoLabel.Left := WizardForm.SelectDirLabel.Left;
  InfoLabel.Top := WizardForm.SelectDirLabel.Top + WizardForm.SelectDirLabel.Height + ScaleY(8);
  InfoLabel.Width := WizardForm.SelectDirPage.Width - InfoLabel.Left - ScaleX(24);
  InfoLabel.Height := ScaleY(42);
  InfoLabel.WordWrap := True;
  InfoLabel.Caption :=
    'HomePrep Server is self-contained. Python, Node.js and other development ' +
    'runtimes are already bundled. Household data and backups are kept in ' +
    '%ProgramData%\HomePrep and are preserved across upgrades.';
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  { Stop either the current service or a legacy foreground/autostart process before upgrade. }
  Exec(ExpandConstant('{sys}\sc.exe'), 'stop HomePrepServer', '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM HomePrepServer.exe /F', '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM HomePrepServerManager.exe /F', '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode);

  { Older installer builds used HKLM Run instead of a Windows service. }
  RegDeleteValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Run', 'HomePrepServer');
  Result := '';
end;

{ Preparedness data intentionally lives outside the installation directory
  under %ProgramData%\HomePrep and is not removed during uninstall. }
