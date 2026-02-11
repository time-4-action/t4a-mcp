@echo off
REM Push MCP Server Docker image to registry (Windows)

echo Pushing MCP Server Docker image...
echo ==================================
echo.

REM Push latest tag
echo Pushing etiamsi/t4a-mcp:latest...
docker push etiamsi/t4a-mcp:latest

if %errorlevel% neq 0 (
    echo.
    echo Push failed!
    exit /b %errorlevel%
)

echo.
echo Push complete!
echo.
echo Image pushed to Docker Hub:
echo   etiamsi/t4a-mcp:latest
echo.
