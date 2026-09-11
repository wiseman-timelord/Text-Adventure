@echo off
cd /d "%~dp0" 2>nul || (
    echo  [ERROR] Cannot access script directory.
    pause & exit /b 1
)

:menu
cls
echo ================================================================================
echo     Text-Adventure - Batch Menu
echo ================================================================================
echo.
echo.
echo.
echo.
echo.
echo.
echo.
echo.
echo.
echo     1) Run Text Adventure
echo.
echo     2) Installer / Environment Tools
echo.
echo.
echo.
echo.
echo.
echo.
echo.
echo.
echo.
echo --------------------------------------------------------------------------------
set /p choice="Selection; Menu Options = 1-2, Exit Menu = X: "

if "%choice%"=="1" goto run_game
if "%choice%"=="2" goto install_menu
if /I "%choice%"=="X" goto exit_script

echo Invalid choice. Please try again.
pause
goto menu

:run_game
cls
echo ================================================================================
echo     Text-Adventure - Launching Game
echo ================================================================================
echo.
echo Starting Text Adventure...
python launcher.py
echo.
echo --------------------------------------------------------------------------------
echo Game has exited. Returning to menu...
timeout /t 2 >nul
goto menu

:install_menu
python installer.py
echo.
echo Returning to main menu...
timeout /t 1 >nul
goto menu

:exit_script
exit
