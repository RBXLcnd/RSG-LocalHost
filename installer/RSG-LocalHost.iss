; Inno Setup script for RSG LocalHost. Built by GitHub Actions (see .github/workflows/build.yml).
; Per-user install (no admin needed). Updating = running a newer installer over the old one; the user's
; data is in %APPDATA%\RSG LocalHost and is never overwritten.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "RSG LocalHost"
#define AppExe  "RSG LocalHost.exe"

[Setup]
AppId={{B7C3E2A4-5D1F-4E8B-9A62-3F0C7D9E4B15}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=RSG
AppPublisherURL=https://github.com/RBXLcnd/RSG-LocalHost
AppSupportURL=https://github.com/RBXLcnd/RSG-LocalHost/issues
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\installer_out
OutputBaseFilename=RSG-LocalHost-Setup
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
LicenseFile=..\LICENSE.md
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\RSG LocalHost\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; rsg://join/host:port invite links open RSG LocalHost (per user). The app also registers itself on start.
Root: HKCU; Subkey: "Software\Classes\rsg"; ValueType: string; ValueName: ""; ValueData: "URL:RSG LocalHost"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\rsg"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\rsg\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"",0"
Root: HKCU; Subkey: "Software\Classes\rsg\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
// Settings, profiles and the Discord sign-in live in %APPDATA%\RSG LocalHost so updates never touch them.
// On uninstall, ask before removing them (a silent uninstall keeps them).
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    if MsgBox('Also delete your saved settings, profiles and Discord sign-in?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      DelTree(ExpandConstant('{userappdata}\RSG LocalHost'), True, True, True);
end;
