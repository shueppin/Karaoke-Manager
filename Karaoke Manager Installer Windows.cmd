:: A template for this code can be found at https://github.com/shueppin/Python-App-Installer/blob/main/installer_templates/windows_cmd.cmd

@echo off
cls
setlocal


:: Variables to set for your program:
:: - source_code_url: For example GitHub URL for the user to see the program's code
:: - program_size: The estimated disk space for a full installation of your program
:: - python_release_url: The URL to the python release page (like: https://www.python.org/downloads/release/python-3128/)
:: - python_zip_download_url: The URL of the "windows embeddable package (64-bit)" on the release page of the python version.
:: - requirements_file_url: The URL to your requirements.txt file (only the modules which the initial file needs). Leave empty if not needed.
:: - initial_file_url: The URL for the file which should be downloaded and run. This could be an updater or an installer written in python.
:: - shortcut_icon_url: The url for the icon for the shortcut (with no icon URL it will just create a simple shortcut with the python icon).
:: - show_console: Whether the installed python script should show an output console or not (this can theoretically be changed later).
:: - arguments: The arguments with which the downloaded python file is started when running the program.
:: - create_shortcut_in_programs: Whether it should create a shortcut in the programs directory.
:: ATTENTION: Every "%" in all URLs has to be replaced with "%%", otherwise it will not work. Best would be if there were no "%" in the URL at all.
set "program_name=Karaoke Manager"
set "source_code_url=https://github.com/shueppin/Karaoke-Manager"
set "program_size=250MB"
set "python_release_url=https://www.python.org/downloads/release/python-31210/"
set "python_zip_download_url=https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"
set "requirements_file_url=https://raw.githubusercontent.com/shueppin/Karaoke-Manager/refs/heads/main/requirements.txt"
set "initial_file_url=https://raw.githubusercontent.com/shueppin/Karaoke-Manager/refs/heads/main/main.py"
set "shortcut_icon_url=https://raw.githubusercontent.com/shueppin/Karaoke-Manager/refs/heads/main/icon.ico"
set "show_console=..."
set "arguments=..."
set "create_shortcut_in_programs=..."


:: Different colors:
:: - ca = answer color, used for the user's answers to the questions
:: - ce = error color, used for all errors
:: - cf = file color, used for files and filepaths.
:: - ci = information color, used for all the information of other scripts (like the python output)
:: - cl = link color, used for URLs
:: - cm = main color, used for most information
:: - cq = question color, used for questions which the user needs to answer
:: - cr = reset color, used to reset all color codes
set "ca=[37m"
set "ce=[31m"
set "cf=[33m"
set "ci=[90m"
set "cl=[94m"
set "cm=[36m"
set "cq=[96m"
set "cr=[0m"


:: Display installer information and ask for permission to download files
title %program_name% Installer
echo.
echo %cm%This is the installer for %program_name%.
echo The source code is available under %cl%%source_code_url%
echo %cm%The program needs about %program_size% of free space.
echo.
echo.
echo The installer will download Python and PIP from the following URLs:
echo 1. %cl%%python_release_url% %cm%
echo 2. %cl%https://bootstrap.pypa.io/get-pip.py %cm%
echo Python and PIP will be installed in a separate directory only for this program.
echo.
echo The installer will also download the following files for the program to be installed correctly:
echo 1. %cl%%requirements_file_url% %cm%
echo 2. %cl%%initial_file_url% %cm%
echo.


:: Ask for permission to download files from the internet
:askConsent
echo.
set /p userPermission=%cq%Do you agree to proceed with the download? (yes/no): %ca%
if /I "%userPermission%"=="y" goto UserPermission
if /I "%userPermission%"=="yes" goto UserPermission
if /I "%userPermission%"=="n" goto noUserPermission
if /I "%userPermission%"=="no" goto noUserPermission
echo Invalid input. Please enter "yes" or "no".
goto askConsent

:UserPermission

:: Ask for Installation Directory. The default is the user's program directory.
set "defaultPath=%LOCALAPPDATA%\Programs\%program_name%"

:askInstallationPath
echo.
set "installPath="
set /p installPath=%cq%Enter the installation path or leave empty for default (default: %cf%%defaultPath%%cq%): %ca%
if "%installPath%"=="" set "installPath=%defaultPath%"
)


:: If the install Path is not the default path then continue with the script and ask for confirmation, otherwise just jump over the confirmation part.
if /I "%installPath%"=="%defaultPath%" goto correctPath

echo CRASH PREVENTION >nul
:: The line before is to prevent crashes because a label is directly after an if command

:: Ask for confirmation if the path is not the default path.
:customPathConfirmation
echo.
echo %cm%You entered a custom installation path: %cf%%installPath%
set /p confirmPath=%cq%Is this path correct (no typos)? (yes/no): %ca%
if /I "%confirmPath%"=="y" goto correctPath
if /I "%confirmPath%"=="yes" goto correctPath
if /I "%confirmPath%"=="n" goto askInstallationPath
if /I "%confirmPath%"=="no" goto askInstallationPath
echo Invalid input. Please enter "yes" or "no".
goto customPathConfirmation


:correctPath

:: Check if the path contains either files or folders. If the path doesn't exist then also create a directory.
for %%i in ("%installPath%\*") do goto directoryNotEmpty
for /D %%i in ("%installPath%\*") do goto directoryNotEmpty
if not exist "%installPath%" mkdir "%installPath%"


:: Download the Python zip file
echo.
echo %cm%Downloading Python zip file from %cl%%python_zip_download_url% %ci%
set "pythonZipPath=%installPath%\python_downloaded.zip"
curl -o "%pythonZipPath%" "%python_zip_download_url%" -s
if errorlevel 1 goto downloadError


:: Unpack the zip file into a directory and delete the file.
echo.
echo %cm%Unpacking Python zip file %ci%
set "pythonUnpackDir=%installPath%\python"
mkdir "%pythonUnpackDir%"
tar -xf "%pythonZipPath%" -C "%pythonUnpackDir%"
if errorlevel 1 goto unpackError
del "%pythonZipPath%"


:: Download "get-pip.py"
echo.
echo %cm%Downloading %cf%get-pip.py %ci%
set "getPipUrl=https://bootstrap.pypa.io/get-pip.py"
set "getPipPath=%installPath%\get-pip.py"
curl -o "%getPipPath%" "%getPipUrl%" -s
if errorlevel 1 goto downloadError


:: Execute "get-pip.py" and remove it afterwards
echo.
echo %cm%Installing pip using the file %cf%get-pip.py %ci%
set "pythonExe=%pythonUnpackDir%\python.exe"
"%pythonExe%" "%getPipPath%" --no-warn-script-location
if errorlevel 1 goto executionError
del "%getPipPath%"


:: Find the "python---._pth" file. This has to be done using a search for the file extension because the name contains the actual version
echo.
echo %cm%Modifying the %cf%python._pth %cm%file to allow usage of PIP %ci%
for %%F in ("%pythonUnpackDir%\*._pth") do set "pthFile=%%F"
if not defined pthFile goto fileNotFoundError


:: Change the "python---._pth" file to be able to use PIP.
setlocal enabledelayedexpansion
(
    for /f "delims=" %%i in ('type "%pthFile%"') do (
        set "line=%%i"

        :: Replace the import statement
        set "line=!line:#import site=import site!"

        echo !line!
    )
) > "%pthFile%.tmp"
:: Rename the temporary file to have the original filename
move /y "%pthFile%.tmp" "%pthFile%" >nul
endlocal
if errorlevel 1 goto fileModifyError


:: Check if there is a requirements_file_url
if "%requirements_file_url%"=="" goto noRequirementsFileNeeded


:: Download the requirements file using the filename from the URL
echo.
echo %cm%Downloading the requirements file from %cl%%requirements_file_url% %ci%
curl "%requirements_file_url%" --output-dir "%installPath%" -O -s
if errorlevel 1 goto downloadError


:: Get the filename from the downloaded file and set the filepath
timeout /t 1 /nobreak > nul
for /f "delims=" %%f in ('dir "%installPath%" /b /a-d /od') do (
    set "requirementsFileName=%%f"
)
set "requirementsPath=%installPath%\%requirementsFileName%"
if errorlevel 1 goto getFileNameError


:: Install the requirements from the requirements file
echo.
echo %cm%Installing requirements from %cf%%requirementsFileName% %ci%
"%pythonExe%" -m pip install -r "%requirementsPath%" --no-warn-script-location
if errorlevel 1 goto executionError


:noRequirementsFileNeeded

:: Download the initial file using the filename from the URL
echo.
echo %cm%Downloading the initial file from %cl%%initial_file_url% %ci%
curl "%initial_file_url%" --output-dir "%installPath%" -O -s
if errorlevel 1 goto downloadError


:: Get the filename from the downloaded file and set the filepath
timeout /t 1 /nobreak > nul
for /f "delims=" %%f in ('dir "%installPath%" /b /a-d /od') do (
    set "initialFileName=%%f"
)
set "initialFilePath=%installPath%\%initialFileName%"
if errorlevel 1 goto getFileNameError


:: Change the show_console variable so it is in the format which Python and VBS want
if /I "%show_console%"=="true" (
    set "show_console=True"
) else (
    set "show_console=False"
)


:: Configure the python.exe file to run the main program by using an extra file called "sitecustomize.py"
echo.
echo %cm%Creating %cf%sitecustomize.py %cm%to run the Program when executing %cf%python.exe %cm% or %cf%pythonw.exe %ci%
set "sitecustomizePath=%pythonUnpackDir%\sitecustomize.py"

:: Create the Python file
echo import sys >> "%sitecustomizePath%"
echo.  >> "%sitecustomizePath%"
echo SHOW_CONSOLE = %show_console% >> "%sitecustomizePath%"
echo.  >> "%sitecustomizePath%"
echo # Check for passed arguments. If the exe file is used to run a python file, it will have some arguments, thus it should not call itself again. >> "%sitecustomizePath%"
echo if sys.argv == ['']: >> "%sitecustomizePath%"
echo     import subprocess >> "%sitecustomizePath%"
echo. >> "%sitecustomizePath%"
echo     # Use subprocess to run the script with or without a console window >> "%sitecustomizePath%"
echo     if SHOW_CONSOLE: >> "%sitecustomizePath%"
echo         subprocess.Popen([r"%pythonUnpackDir%\python.exe", r"%initialFilePath%"], creationflags=subprocess.CREATE_NEW_CONSOLE) >> "%sitecustomizePath%"
echo     else: >> "%sitecustomizePath%"
echo         subprocess.Popen([r"%pythonUnpackDir%\pythonw.exe", r"%initialFilePath%"]) >> "%sitecustomizePath%"
echo.  >> "%sitecustomizePath%"
echo     sys.exit() >> "%sitecustomizePath%"

if errorlevel 1 goto fileModifyError


:: Download the shortcut icon if there is a URL for it
if "%shortcut_icon_url%"=="" goto noShortcutIcon

echo.
echo %cm%Downloading %cf%shortcut_icon.ico %cm%from %cl%%shortcut_icon_url% %ci%
set "shortcutIconPath=%installPath%\shortcut_icon.ico"
curl -o "%shortcutIconPath%" "%shortcut_icon_url%" -s
if errorlevel 1 goto downloadError


:noShortcutIcon


:: Create the shortcut in the installation folder
echo.
echo %cm%Creating the shortcut in the installation directory %ci%
set "createShortcutVBSFile=%installPath%\create_shortcut.vbs"
set "shortcutFile=%installPath%\%program_name%.lnk"

:: Create the VBScript that can create windows shortcuts
echo ' Define variables >> "%createShortcutVBSFile%"
echo Dim SHOW_CONSOLE, SHELL, shortcut >> "%createShortcutVBSFile%"
echo. >> "%createShortcutVBSFile%"
echo SHOW_CONSOLE = %show_console% >> "%createShortcutVBSFile%"
echo. >> "%createShortcutVBSFile%"
echo Set SHELL = WScript.CreateObject("WScript.Shell") >> "%createShortcutVBSFile%"
echo Set shortcut = shell.CreateShortcut("%shortcutFile%") >> "%createShortcutVBSFile%"
echo. >> "%createShortcutVBSFile%"
echo ' Define shortcut values >> "%createShortcutVBSFile%"
echo If SHOW_CONSOLE Then >> "%createShortcutVBSFile%"
echo shortcut.TargetPath = "%pythonUnpackDir%\python.exe" >> "%createShortcutVBSFile%"
echo Else >> "%createShortcutVBSFile%"
echo shortcut.TargetPath = "%pythonUnpackDir%\pythonw.exe" >> "%createShortcutVBSFile%"
echo End If >> "%createShortcutVBSFile%"
echo. >> "%createShortcutVBSFile%"
echo shortcut.Description = "%program_name%" >> "%createShortcutVBSFile%"
:: The following lihne checks whether there is a shortcut icon, and if not it just creates the shortcut without this.
if "%shortcut_icon_url%" NEQ "" echo shortcut.IconLocation = "%shortcutIconPath%" >> "%createShortcutVBSFile%"
echo shortcut.WorkingDirectory = "%installPath%" >> "%createShortcutVBSFile%"
echo shortcut.Save >> "%createShortcutVBSFile%"
echo. >> "%createShortcutVBSFile%"
echo ' Clean up >> "%createShortcutVBSFile%"
echo Set shortcut = Nothing >> "%createShortcutVBSFile%"
echo Set shell = Nothing >> "%createShortcutVBSFile%"

if errorlevel 1 goto fileModifyError

:: Execute the created VBScript and delete it
cscript "%createShortcutVBSFile%"
if errorlevel 1 goto executionError


:: Copying the shortcut to the programs folder if the specific variable is set to true
if /I "%create_shortcut_in_programs%" NEQ "true" goto noShortcutInPrograms
echo.
echo %cm%Copying the shortcut to the programs directory %ci%
copy "%shortcutFile%" "%APPDATA%\Microsoft\Windows\Start Menu\Programs" >nul
if errorlevel 1 goto fileModifyError


:noShortcutInPrograms


:: Final message
echo.
echo.
echo.
echo %cm%The installation process is completed.
echo.
echo %cm%The program was installed at %cf%%installPath%
if /I "%create_shortcut_in_programs%"=="true" echo %cm%A shortcut to the program was also created at %cf%%APPDATA%\Microsoft\Windows\Start Menu\Programs
echo.
echo %cm%You can now follow further instructions from the program if there are any.
echo The program will be started soon, then you can close this window.
echo.


:: Execute the start file.
timeout /t 5
echo.
if /I "%show_console%"=="true" "%pythonUnpackDir%\python.exe" "%initialFilePath%"
if /I "%show_console%" NEQ "true" "%pythonUnpackDir%\pythonw.exe" "%initialFilePath%"
if errorlevel 1 goto executionError


goto end


:: Error Jump points
:directoryNotEmpty
echo.
echo %ce%The selected installation directory is not empty.
echo This could be due to the program already being installed.
echo Please choose an empty directory.
goto askInstallationPath


:downloadError
echo.
echo %ce%An error occurred while trying to download this file.
goto termination


:executionError
echo.
echo %ce%An error occurred while trying to execute this command.
goto termination


:fileModifyError
echo.
echo %ce%An error has occurred while trying to modify the content of this file.
goto termination


:fileNotFoundError
echo.
echo %ce%This file couldn't be found.
goto termination


:getFileNameError
echo.
echo %ce%Couldn't get the name of the downloaded file.
goto termination


:noUserPermission
echo.
echo %ce%Installation terminated since no consent to download was given.
echo If this was done by accident, execute the installer again.
goto end


:unpackError
echo.
echo %ce%An error occurred while trying to unpack the python interpreter.
goto termination


:: End jump points
:termination
echo %ce%Installation Terminated.
echo.
echo The Script was terminated due to an error.
echo To try to install this again please delete the contents of the directory at %installPath%
goto end


:end
echo.
echo %cr%
pause

endlocal
