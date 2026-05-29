#define MyAppName "Finance Pro"
#define MyAppVersion "1.1.2"
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
; Launch the app via checkbox option in interactive mode
Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
#ifdef UNICODE
  #define AW "W"
#else
  #define AW "A"
#endif

function SetEnvironmentVariable(lpName, lpValue: String): Boolean;
external 'SetEnvironmentVariable{#AW}@kernel32.dll stdcall';

function GetEnvironmentVariable(lpName: String; lpValue: String; nSize: Integer): Integer;
external 'GetEnvironmentVariable{#AW}@kernel32.dll stdcall';

function InitializeSetup(): Boolean;
var
  PathBuf: String;
  PathLen: Integer;
  NewPath: String;
  P: Integer;
  PathPart: String;
  RemainingPath: String;
begin
  // Clear python environment variables
  SetEnvironmentVariable('PYTHONHOME', '');
  SetEnvironmentVariable('PYTHONPATH', '');

  // Clean PATH variable from any inherited PyInstaller _MEI directories
  PathLen := 4096;
  SetLength(PathBuf, PathLen);
  PathLen := GetEnvironmentVariable('PATH', PathBuf, PathLen);
  if PathLen > 0 then
  begin
    SetLength(PathBuf, PathLen);
    RemainingPath := PathBuf;
    NewPath := '';
    while Length(RemainingPath) > 0 do
    begin
      P := Pos(';', RemainingPath);
      if P > 0 then
      begin
        PathPart := Copy(RemainingPath, 1, P - 1);
        RemainingPath := Copy(RemainingPath, P + 1, Length(RemainingPath) - P);
      end
      else
      begin
        PathPart := RemainingPath;
        RemainingPath := '';
      end;
      
      // If the path part does not contain '_MEI', keep it
      if Pos('_MEI', PathPart) = 0 then
      begin
        if NewPath <> '' then
          NewPath := NewPath + ';' + PathPart
        else
          NewPath := PathPart;
      end;
    end;
    SetEnvironmentVariable('PATH', NewPath);
  end;
  Result := True;
end;
