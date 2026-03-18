#!/bin/bash
# Launch all 9 provider agents on ports 8010-8018
# Each wraps a different travel API service

SERVICES=(
    "hotel-1:8010"
    "hotel-2:8011"
    "restaurant-1:8012"
    "restaurant-2:8013"
    "restaurant-3:8014"
    "flight-1:8015"
    "car-rental-1:8016"
    "tour-guide-1:8017"
    "museum-1:8018"
)

PIDS=()

cleanup() {
    echo ""
    echo "Shutting down all providers..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null
    done
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "=== Starting all provider agents ==="
echo ""

for entry in "${SERVICES[@]}"; do
    IFS=":" read -r service port <<< "$entry"
    echo "Starting $service on port $port..."
    SERVICE_NAME="$service" SERVICE_PORT="$port" python provider/main.py &
    PIDS+=($!)
done

echo ""
echo "=== All providers running ==="
echo ""
echo "  hotel-1       → http://localhost:8010"
echo "  hotel-2       → http://localhost:8011"
echo "  restaurant-1  → http://localhost:8012"
echo "  restaurant-2  → http://localhost:8013"
echo "  restaurant-3  → http://localhost:8014"
echo "  flight-1      → http://localhost:8015"
echo "  car-rental-1  → http://localhost:8016"
echo "  tour-guide-1  → http://localhost:8017"
echo "  museum-1      → http://localhost:8018"
echo ""
echo "Press Ctrl+C to stop all."

wait
