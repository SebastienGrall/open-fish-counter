#define MyAppName "Open Fish Counter"
#define MyAppVersion "1.0.0-alpha"
#define MyAppPublisher "Sebastien Grall"
#define MyAppExeName "OpenFishCounter.exe"
#define MyAppSourceDir "..\..\dist\OpenFishCounter"
#define MyAppIcon "..\..\assets\icons\open-fish-counter.ico"

[Setup]
AppId={{fca1cb84-ec76-5e0c-b73b-d370621b80b3}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\OpenFishCounter
DefaultGroupName={#MyAppName}
SetupIconFile={#MyAppIcon}
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=OpenFishCounter-Setup-{#MyAppVersion}-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName={#MyAppName} {#MyAppVersion}
SetupLogging=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis supplémentaires :"; Flags: unchecked

[Files]
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function GenTLProducerAvailable(): Boolean;
var
  GenTLPath: string;
begin
  GenTLPath := GetEnv('GENICAM_GENTL64_PATH');

  if GenTLPath = '' then
    RegQueryStringValue(
      HKLM64,
      'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
      'GENICAM_GENTL64_PATH',
      GenTLPath
    );

  Result := GenTLPath <> '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and not GenTLProducerAvailable() then
  begin
    MsgBox(
      'Open Fish Counter est installé.' + #13#10 + #13#10 +
      'La webcam OpenCV peut être utilisée immédiatement.' + #13#10 + #13#10 +
      'Pour utiliser une caméra The Imaging Source IC4, installez également ' +
      'le GenTL Producer GigE Vision 64 bits, puis redémarrez la session Windows.',
      mbInformation,
      MB_OK
    );
  end;
end;
