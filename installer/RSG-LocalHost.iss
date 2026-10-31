; Inno Setup script for RSG LocalHost. Built by GitHub Actions (see .github/workflows/build.yml).
; Per-user install (no admin needed): the app stores its settings next to the exe, so it must live
; in a folder the user can write to.

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

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; settings (contains the Discord key) and cache created by the app next to the exe
Type: files;          Name: "{app}\mattslocalhost_data.json"
Type: filesandordirs; Name: "{app}\.localhost_cache"
