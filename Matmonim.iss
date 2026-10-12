; Inno Setup 6 script - Matmonim
[Setup]
AppName=Matmonim
AppVersion=1.0
AppPublisher=Matmonim
DefaultDirName={localappdata}\Matmonim
DefaultGroupName=Matmonim
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=Matmonim_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=Matmonim
SetupIconFile=matmonim.ico
UninstallDisplayIcon={app}\matmonim.ico

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: checkedonce

[Files]
Source: "app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "launch.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "stop.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "matmonim.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: ".streamlit\*"; DestDir: "{app}\.streamlit"; Flags: ignoreversion
Source: "python_portable\*"; DestDir: "{app}\python_portable"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "books\*"; DestDir: "{app}\books"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist uninsneveruninstall skipifsourcedoesntexist

[Icons]
Name: "{autoprograms}\Matmonim"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\launch.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\matmonim.ico"
Name: "{autoprograms}\Matmonim - Stop"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\stop.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\matmonim.ico"
Name: "{autodesktop}\Matmonim"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\launch.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\matmonim.ico"; Tasks: desktopicon

[Run]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\launch.vbs"""; WorkingDir: "{app}"; Description: "Launch Matmonim"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\stop.vbs"""; Flags: runhidden; RunOnceId: "StopServer"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\python_portable"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\.streamlit"
