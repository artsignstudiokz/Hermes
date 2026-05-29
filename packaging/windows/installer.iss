; Hermes — Inno Setup script
; Builds BaiCoreHermes-Setup-1.0.0.exe (browser-style install UX in Russian).
;
; Build:  iscc packaging\windows\installer.iss   (after PyInstaller produced dist\Hermes.exe)

#define AppName       "Hermes"
#define AppPublisher  "BAI Core"
#define AppURL        "https://baicore.kz"
#define AppVersion    "1.0.0"
#define AppExeName    "Hermes.exe"
#define AppId         "{{6F1C2A3D-4E7B-4D7C-9D2A-AA01B7C3D5E2}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVerName=Hermes {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
AppVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoProductName={#AppName}
VersionInfoCopyright=© BAI Core. All rights reserved.

DefaultDirName={localappdata}\Programs\Hermes
DefaultGroupName=Hermes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
DisableWelcomePage=no

OutputBaseFilename=Hermes-Setup-{#AppVersion}
OutputDir=..\..\dist\installer
SetupIconFile=assets\app-icon.ico
WizardStyle=modern
WizardImageFile=assets\installer-banner.bmp
WizardSmallImageFile=assets\installer-header.bmp
WizardImageStretch=no
LicenseFile=assets\license.rtf

Compression=lzma2/ultra64
SolidCompression=yes
ShowLanguageDialog=auto
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName=Hermes

; Seamless in-place upgrade. Inno detects an existing install by AppId,
; force-closes the running Hermes.exe before replacing files, then
; relaunches the new version when the installer finishes. Combined with
; the data dir living in %APPDATA%\BAI Core\Hermes (outside the install
; tree), the user keeps their vault, DB, strategies, broker config etc.
CloseApplications=force
CloseApplicationsFilter=Hermes.exe
RestartApplications=yes

ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "Дополнительно:"
Name: "startupicon"; Description: "Запускать Hermes при старте Windows"; GroupDescription: "Дополнительно:"; Flags: unchecked

[Files]
; PyInstaller onedir output: dist\Hermes\ contains Hermes.exe + all DLLs/PYDs.
; This is dramatically more reliable than onefile (no _MEIPASS unpacking,
; every Python module is just on disk where the import machinery expects it).
Source: "..\..\dist\Hermes\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\app-icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";              Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\app-icon.ico"
Name: "{group}\Удалить {#AppName}";      Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";      Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\app-icon.ico"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}";        Filename: "{app}\{#AppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Запустить Hermes"; Flags: nowait postinstall skipifsilent
