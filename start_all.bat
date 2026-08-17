@echo off
REM SmartRetailX - Start All Microservices (Phase 2)
REM Run this from the project root: SmartRetailX\
REM Requires: py -m pip install -r requirements.txt

setlocal

REM ── Ensure project root is on PYTHONPATH so relative imports resolve ──────────
set PYTHONPATH=%~dp0

echo ============================================
echo  SmartRetailX Microservices Launcher
echo  Phase 2: JWT + SQS Integration
echo ============================================
echo.
echo  PYTHONPATH set to: %PYTHONPATH%
echo.
echo  Optional AWS env vars (leave unset for local-only mode):
echo    SQS_QUEUE_URL  - Full SQS queue URL for order events
echo    AWS_REGION     - AWS region (default: eu-west-1)
echo    JWT_SECRET_KEY - JWT signing secret (default key used if unset)
echo.

echo [1/4] Starting User Service on port 8001...
start "User Service :8001" cmd /k "set PYTHONPATH=%~dp0 && py -m uvicorn user_service.main:app --reload --port 8001"
timeout /t 2 /nobreak >nul

echo [2/4] Starting Product Service on port 8002...
start "Product Service :8002" cmd /k "set PYTHONPATH=%~dp0 && py -m uvicorn product_service.main:app --reload --port 8002"
timeout /t 2 /nobreak >nul

echo [3/4] Starting Order Service on port 8003...
start "Order Service :8003" cmd /k "set PYTHONPATH=%~dp0 && py -m uvicorn order_service.main:app --reload --port 8003"
timeout /t 2 /nobreak >nul

echo [4/4] Starting Inventory Service on port 8004...
start "Inventory Service :8004" cmd /k "set PYTHONPATH=%~dp0 && py -m uvicorn inventory_service.main:app --reload --port 8004"
timeout /t 2 /nobreak >nul

echo.
echo ============================================
echo  All services starting. Swagger UIs:
echo   User Service:      http://localhost:8001/docs
echo   Product Service:   http://localhost:8002/docs
echo   Order Service:     http://localhost:8003/docs
echo   Inventory Service: http://localhost:8004/docs
echo.
echo  Health checks:
echo   http://localhost:8001/health
echo   http://localhost:8002/health
echo   http://localhost:8003/health
echo   http://localhost:8004/health
echo.
echo  Frontend:
echo   Open frontend\index.html in your browser
echo.
echo  Default credentials:
echo   Admin:    admin@smartretailx.com / AdminPass123!
echo   Customer: customer@smartretailx.com / CustomerPass123!
echo ============================================
endlocal
