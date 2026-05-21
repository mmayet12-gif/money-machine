@echo off
set SCRIPT_DIR=%~dp0
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
  "%LocalAppData%\Programs\Python\Python312\python.exe" "%SCRIPT_DIR%money-machine.py" %*
  exit /b %ERRORLEVEL%
)
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
  "%LocalAppData%\Programs\Python\Python311\python.exe" "%SCRIPT_DIR%money-machine.py" %*
  exit /b %ERRORLEVEL%
)
python "%SCRIPT_DIR%money-machine.py" %*
if %ERRORLEVEL%==0 exit /b 0

py "%SCRIPT_DIR%money-machine.py" %*
if %ERRORLEVEL%==0 exit /b 0

echo No usable Python executable found. Install Python and ensure either 'python' or 'py' is available.
exit /b 1
