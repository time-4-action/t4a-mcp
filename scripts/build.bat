@echo off
REM Fast build script for MCP Server Docker image (Windows)

echo Building MCP Server Docker image...
echo ==================================
echo.

REM Build with BuildKit for faster builds
set DOCKER_BUILDKIT=1
docker build --progress=plain -t etiamsi/t4a-mcp:latest .

if %errorlevel% neq 0 (
    echo.
    echo Build failed!
    exit /b %errorlevel%
)

echo.
echo Build complete!
echo.
echo To run the server:
echo   docker-compose up -d
echo.
echo To view logs:
echo   docker-compose logs -f
echo.
echo To stop:
echo   docker-compose down
