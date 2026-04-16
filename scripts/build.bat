@echo off
REM Fast build script for MCP Server Docker image (Windows)
REM Usage: build.bat [--latest] [--dev]

set IMAGE=time4action/t4a-mcp

REM Generate timestamp tag (YYYYMMDD-HHMMSS)
for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set DATESTAMP=%%c%%b%%a
for /f "tokens=1-2 delims=:." %%a in ('time /t') do set TIMESTAMP=%%a%%b00
set TAG=%DATESTAMP%-%TIMESTAMP: =%

set EXTRA_TAGS=
:parse_args
if "%1"=="" goto :done_args
if "%1"=="--latest" set EXTRA_TAGS=%EXTRA_TAGS% -t %IMAGE%:latest
if "%1"=="--dev" set EXTRA_TAGS=%EXTRA_TAGS% -t %IMAGE%:dev
shift
goto :parse_args
:done_args

echo Building MCP Server Docker image...
echo ==================================
echo.

REM Build with BuildKit for faster builds
set DOCKER_BUILDKIT=1
docker build --progress=plain -t %IMAGE%:%TAG%%EXTRA_TAGS% .

if %errorlevel% neq 0 (
    echo.
    echo Build failed!
    exit /b %errorlevel%
)

echo.
echo Build complete!
echo   Tagged: %IMAGE%:%TAG%
echo %EXTRA_TAGS% | findstr /c:"latest" >nul && echo   Tagged: %IMAGE%:latest
echo %EXTRA_TAGS% | findstr /c:"dev" >nul && echo   Tagged: %IMAGE%:dev
echo.
echo To run the server:
echo   docker-compose up -d
