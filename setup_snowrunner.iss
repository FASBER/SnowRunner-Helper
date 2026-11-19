; SnowRunner Helper v31 — Windows installation package
; Run build_installer_windows.bat on Windows to produce the signed/unsigned local installer.
; An approved SnowRunner-styled mock-up is a DESIGN REFERENCE. Inno Setup's
; native directory-selection dialog remains a Windows wizard, not a 1:1 mock-up.
#define MyAppName "SnowRunner Helper"
#define MyAppVersion "0.31.2"
#define MyAppExeName "SnowRunnerHelper.exe"

[Setup]
; KEEP AppId STABLE between versions, otherwise updates become side-by-side installs.
AppId=SnowRunnerCraftAssistant.CommunityEdition
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v0.31.2
AppPublisher=SnowRunner Helper Community Project
DefaultDirName={localappdata}\Programs\SnowRunner Helper
UsePreviousAppDir=yes
DisableDirPage=no
DirExistsWarning=auto
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
WizardStyle=modern
WizardImageFile=installer_assets\wizard_side.bmp
WizardSmallImageFile=installer_assets\wizard_small.bmp
OutputDir=installer_build
OutputBaseFilename=SnowRunnerHelper_Setup_v0.31.2
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
AllowNoIcons=yes
MinVersion=10.0

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; A native Windows .exe must exist first. Never include the source-only project
; as if it were a runnable end-user Windows application.
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[InstallDelete]
; Remove only prior application executable and obsolete shortcuts when upgrading v28.
Type: files; Name: "{app}\SnowRunnerCraftAssistant.exe"
Type: files; Name: "{autoprograms}\SnowRunner Craft Assistant.lnk"
Type: files; Name: "{autodesktop}\SnowRunner Craft Assistant.lnk"

; No [UninstallDelete]: personal profile files are never touched.
; Profiles, custom recipes and settings are stored in
; %USERPROFILE%\SnowRunnerCraftAssistant, outside {app} (legacy profile location retained).
