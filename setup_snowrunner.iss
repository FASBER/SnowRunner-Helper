; SnowRunner Helper v31 — Windows installation package
; Run build_installer_windows.bat on Windows to produce the signed/unsigned local installer.
; An approved SnowRunner-styled mock-up is a DESIGN REFERENCE. Inno Setup's
; native directory-selection dialog remains a Windows wizard, not a 1:1 mock-up.
#define MyAppName "SnowRunner Helper"
#define MyAppVersion "0.31.10"
#define MyAppExeName "SnowRunnerHelper.exe"

[Setup]
; KEEP AppId STABLE between versions, otherwise updates become side-by-side installs.
AppId=SnowRunnerCraftAssistant.CommunityEdition
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v0.31.10
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
OutputBaseFilename=SnowRunnerHelper_Setup_v0.31.10
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
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent; Check: ShouldOfferLaunchOnFinish

[InstallDelete]
; Remove only prior application executable and obsolete shortcuts when upgrading v28.
Type: files; Name: "{app}\SnowRunnerCraftAssistant.exe"
Type: files; Name: "{autoprograms}\SnowRunner Craft Assistant.lnk"
Type: files; Name: "{autodesktop}\SnowRunner Craft Assistant.lnk"

; No [UninstallDelete]: personal profile files are never touched.
; Profiles, custom recipes and settings are stored in
; %USERPROFILE%\SnowRunnerCraftAssistant, outside {app} (legacy profile location retained).


[Code]
// Existing OTA clients (including v0.31.5) download Setup into this folder.
// The installer must detect that path itself: older installed versions cannot
// retroactively add command line switches to their OTA helper.
function OtaUpdatesDir(): String;
var
  HomeDir: String;
begin
  HomeDir := GetEnv('USERPROFILE');
  if HomeDir = '' then
    Result := ''
  else
    Result := AddBackslash(HomeDir) + 'SnowRunnerCraftAssistant\updates';
end;

function IsOtaInstall(): Boolean;
var
  I: Integer;
  UpdateDir: String;
begin
  Result := False;
  // Explicit marker is used by new OTA clients after v0.31.10.
  for I := 1 to ParamCount do
  begin
    if CompareText(ParamStr(I), '/OTA=1') = 0 then
    begin
      Result := True;
      Exit;
    end;
  end;
  // Backward compatibility with v0.31.5 OTA: detect its downloads folder.
  UpdateDir := OtaUpdatesDir();
  if UpdateDir <> '' then
    Result := CompareText(ExpandConstant('{src}'), UpdateDir) = 0;
end;

function ShouldOfferLaunchOnFinish(): Boolean;
begin
  // Do not immediately launch the one-file PyInstaller EXE from OTA Setup.
  // The user starts it after the installer is fully closed.
  // Manual installs keep the normal optional "Launch" checkbox.
  Result := not IsOtaInstall();
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  UpdateDir: String;
begin
  // Write a small diagnostic marker after a successful OTA installation.
  // Avoid writing to application binaries, saves, or personal settings.
  if (CurStep <> ssDone) or (not IsOtaInstall()) then
    Exit;
  UpdateDir := OtaUpdatesDir();
  if (UpdateDir <> '') and DirExists(UpdateDir) then
    SaveStringToFile(AddBackslash(UpdateDir) + 'ota_setup_status_v{#MyAppVersion}.txt',
      'OTA Setup v{#MyAppVersion} completed; launch the application from the shortcut.' + #13#10,
      False);
end;
