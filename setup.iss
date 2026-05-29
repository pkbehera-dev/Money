#define MyAppName "Finance Pro"
#define MyAppVersion "1.1.1"
#define MyAppPublisher "Pradyumna Behera"
#define MyAppExeName "Finance Pro.exe"

[Setup]
; AppId is a unique identifier for this application. Do not use the same AppId value in installers for other applications.
AppId={{D3B39798-B756-4BD3-A0A3-63FA8A8504B6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={userappdata}\{#MyAppName}
DisableDirPage=yes
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=FinanceProSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Detect if the application is running using the Windows Mutex
AppMutex=FinanceProMutexString
; PrivilegesRequired=lowest allows the installer to run without requiring Admin rights, installing to User AppData
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Grab the built executable from PyInstaller output and rename it to the standard MyAppExeName
Source: "dist\Finance Pro v{#MyAppVersion}.exe"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
