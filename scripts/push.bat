@echo off
REM Push MCP Server Docker image to registry (Windows)
REM Usage: push.bat [--latest] [--dev]

set IMAGE=time4action/t4a-mcp

set PUSH_LATEST=0
set PUSH_DEV=0
:parse_args
if "%1"=="" goto :done_args
if "%1"=="--latest" set PUSH_LATEST=1
if "%1"=="--dev" set PUSH_DEV=1
shift
goto :parse_args
:done_args

echo Pushing MCP Server Docker image...
echo ==================================
echo.

REM Find the most recent timestamped tag
for /f "tokens=*" %%t in ('docker images %IMAGE% --format "{{.Tag}}" ^| findstr /r "^[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-"') do (
    set TIMESTAMPED_TAG=%%t
    goto :found
)

echo No timestamped tag found. Build first with build.bat
exit /b 1

:found
echo Pushing %IMAGE%:%TIMESTAMPED_TAG%...
docker push %IMAGE%:%TIMESTAMPED_TAG%

if %errorlevel% neq 0 (
    echo.
    echo Push failed!
    exit /b %errorlevel%
)

if "%PUSH_LATEST%"=="1" (
    echo.
    echo Pushing %IMAGE%:latest...
    docker push %IMAGE%:latest

    if %errorlevel% neq 0 (
        echo.
        echo Push failed!
        exit /b %errorlevel%
    )
)

if "%PUSH_DEV%"=="1" (
    echo.
    echo Pushing %IMAGE%:dev...
    docker push %IMAGE%:dev

    if %errorlevel% neq 0 (
        echo.
        echo Push failed!
        exit /b %errorlevel%
    )
)

echo.
echo Push complete!
echo.
echo Image(s) pushed to Docker Hub:
echo   %IMAGE%:%TIMESTAMPED_TAG%
if "%PUSH_LATEST%"=="1" echo   %IMAGE%:latest
if "%PUSH_DEV%"=="1" echo   %IMAGE%:dev
echo.
