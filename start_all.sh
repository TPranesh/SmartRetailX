#!/usr/bin/env bash
# SmartRetailX - Start All Microservices (Linux/macOS) - Phase 2
# Run from the project root: SmartRetailX/
# Requires: pip install -r requirements.txt

# ── Ensure project root is on PYTHONPATH ─────────────────────────────────────
export PYTHONPATH="$(pwd)"

echo "============================================"
echo " SmartRetailX Microservices Launcher"
echo " Phase 2: JWT + SQS Integration"
echo "============================================"
echo " PYTHONPATH: $PYTHONPATH"
echo ""
echo " Optional AWS vars (leave unset for local-only mode):"
echo "   export SQS_QUEUE_URL=https://sqs.eu-west-1.amazonaws.com/.../SmartRetailX-OrderEvents"
echo "   export AWS_REGION=eu-west-1"
echo "   export JWT_SECRET_KEY=your-strong-secret"
echo ""
echo " Default credentials:"
echo "   Admin:    admin@smartretailx.com / AdminPass123!"
echo "   Customer: customer@smartretailx.com / CustomerPass123!"
echo ""

python -m uvicorn user_service.main:app --reload --port 8001 &
PID1=$!
echo "[1/4] User Service started (PID $PID1) → http://localhost:8001/docs"

python -m uvicorn product_service.main:app --reload --port 8002 &
PID2=$!
echo "[2/4] Product Service started (PID $PID2) → http://localhost:8002/docs"

python -m uvicorn order_service.main:app --reload --port 8003 &
PID3=$!
echo "[3/4] Order Service started (PID $PID3) → http://localhost:8003/docs"

python -m uvicorn inventory_service.main:app --reload --port 8004 &
PID4=$!
echo "[4/4] Inventory Service started (PID $PID4) → http://localhost:8004/docs"

echo ""
echo "All services running. Press Ctrl+C to stop all."
echo "Open frontend/index.html in your browser."
trap "kill $PID1 $PID2 $PID3 $PID4" EXIT
wait
