@echo off

set "RELEASE_NAME=motion-mask-windows"

set "CURRENT_DIR=%~dp0"
set "ROOT_DIR=%~dp0..\.."
cd /d "%ROOT_DIR%"

set "OUTPUT_DIR=%ROOT_DIR%\dist\windows"

if exist "%OUTPUT_DIR%" (
    rmdir /s /q "%OUTPUT_DIR%"
    if exist "%OUTPUT_DIR%" (
        echo ERROR: Failed to remove %OUTPUT_DIR%
        exit /b 1
    )
)

mkdir "%OUTPUT_DIR%"

echo === Building with Nuitka (standalone mode)...

set "PACKAGE_CONFIG=%CURRENT_DIR%\nuitka-package.config.yml"

uv run python -m nuitka ^
    --mode=standalone ^
    --no-deployment-flag=self-execution ^
    --user-package-configuration-file="%PACKAGE_CONFIG%" ^
    --assume-yes-for-downloads ^
    --enable-plugin=no-qt ^
    --output-dir="%OUTPUT_DIR%" ^
    --output-filename=motion-mask.exe ^
    --windows-console-mode=hide ^
    --remove-output ^
    src\motion_mask\main.py


if errorlevel 1 (
    echo Nuitka build failed.
    exit /b 1
)

echo === Nuitka build complete.

set "DIST_DIR=%OUTPUT_DIR%\main.dist"

if not exist "%DIST_DIR%" (
    echo ERROR: main.dist not found. Nuitka may have failed.
    exit /b 1
)

echo === Copying resources...
xcopy /E /I /Y "%ROOT_DIR%\src\motion_mask\avatars" "%DIST_DIR%\avatars"
xcopy /E /I /Y "%ROOT_DIR%\src\motion_mask\landmarkers" "%DIST_DIR%\landmarkers"
xcopy /E /I /Y "%ROOT_DIR%\src\motion_mask\settings" "%DIST_DIR%\settings"

echo === Copying launchers...
xcopy /E /I /Y "%ROOT_DIR%\launchers\windows\*" "%DIST_DIR%\"

echo === Creating archive...
cd /d "%OUTPUT_DIR%"
powershell -NoProfile -Command "Compress-Archive -Path '%DIST_DIR%\*' -DestinationPath '%OUTPUT_DIR%\%RELEASE_NAME%.zip' -Force"

echo === Done
