@echo off

set "RELEASE_NAME=motion-mask-windows"

set "SCRIPT_DIR=%~dp0"

cd /d "$SCRIPT_DIR..\.."

set "PROJECT_DIR=%CD%"

set "OUTPUT_DIR=%PROJECT_DIR%\dist\windows"
set "DIST_DIR=%OUTPUT_DIR%\main.dist"

set "PACKAGE_CONFIG=%SCRIPT_DIR%\nuitka-package.config.yml"

echo ====== SCRIPT_DIR: %SCRIPT_DIR%
echo ====== PROJECT_DIR: %PROJECT_DIR%
echo ====== OUTPUT_DIR: %OUTPUT_DIR%
echo ====== DIST_DIR: %DIST_DIR%
echo ====== PACKAGE_CONFIG: %PACKAGE_CONFIG%

if exist "%OUTPUT_DIR%" (
    rmdir /s /q "%OUTPUT_DIR%"
    if exist "%OUTPUT_DIR%" (
        echo ERROR: Failed to remove %OUTPUT_DIR%
        exit /b 1
    )
)

mkdir "%OUTPUT_DIR%"

exit /b 1

echo === Building with Nuitka (standalone mode)...

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


if not exist "%DIST_DIR%" (
    echo ERROR: main.dist not found. Nuitka may have failed.
    exit /b 1
)

echo === Copying resources...
xcopy /E /I /Y "%PROJECT_DIR%\src\motion_mask\avatars" "%DIST_DIR%\avatars"
xcopy /E /I /Y "%PROJECT_DIR%\src\motion_mask\landmarkers" "%DIST_DIR%\landmarkers"
xcopy /E /I /Y "%PROJECT_DIR%\src\motion_mask\settings" "%DIST_DIR%\settings"

echo === Copying launchers...
xcopy /E /I /Y "%PROJECT_DIR%\launchers\windows\*" "%DIST_DIR%\"

echo === Creating archive...

<<<<<<< HEAD
echo === Before creating archive:
echo ====== DIST_DIR: %DIST_DIR%
echo ====== OUTPUT_DIR: %OUTPUT_DIR%

powershell -NoProfile -Command "Compress-Archive -Path '%DIST_DIR%\*' -DestinationPath '%OUTPUT_DIR%\%RELEASE_NAME%.zip' -Force -Exclude '*.zip'"

echo === After creating archive:
echo ====== DIST_DIR: %DIST_DIR%
echo ====== OUTPUT_DIR: %OUTPUT_DIR%

=======
powershell -NoProfile -Command "Compress-Archive -Path '%DIST_DIR%\*' -DestinationPath '%OUTPUT_DIR%\%RELEASE_NAME%.zip' -Force"
>>>>>>> 44f0bfd (fix: build routine)

echo === Done
