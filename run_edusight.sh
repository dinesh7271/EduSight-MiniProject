#!/usr/bin/env bash
# EduSight — Run Backend & Frontend Development Servers
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "============================================================"
echo " Starting EduSight Academic Early Warning System"
echo "============================================================"

# Kill any existing processes on ports 8000 or 5173 if running
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true

# 1. Start FastAPI Backend from backend directory
echo "→ Starting FastAPI backend on http://127.0.0.1:8000..."
cd backend
python3 -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo -n "  Waiting for backend startup..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
        echo " Ready!"
        break
    fi
    sleep 0.5
    echo -n "."
done

# 2. Start Vite Frontend from frontend directory
echo "→ Starting React/Vite frontend on http://localhost:5173..."
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo "============================================================"
echo " ✓ EduSight is running!"
echo "   Frontend Web UI : http://localhost:5173"
echo "   Backend REST API: http://localhost:8000"
echo "   Swagger Docs    : http://localhost:8000/docs"
echo "============================================================"
echo " Demo Accounts:"
echo "   Student: username='student1', password='student123'"
echo "   Teacher: username='faculty1', password='faculty123'"
echo "   Admin  : username='admin',    password='admin123'"
echo " Or click 'Create Account' on the login page to register!"
echo "============================================================"
echo "Logs: tail -f backend.log frontend.log"
echo "Press CTRL+C or run 'fuser -k 8000/tcp 5173/tcp' to stop."

# Wait on background processes
wait $BACKEND_PID $FRONTEND_PID
