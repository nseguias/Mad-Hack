"""All travel service configs in one place."""

API_BASE = "https://hacketon-18march-api.orcaplatform.ai"

SERVICES = {
    "hotel-1": {
        "name": "Hotel 1",
        "base_url": f"{API_BASE}/hotel-1",
        "api_key": "hotel-1-key-abc123",
        "port": 8010,
        "description": "Hotel room reservations — search rooms, check availability, get pricing, book and cancel reservations",
    },
    "hotel-2": {
        "name": "Hotel 2",
        "base_url": f"{API_BASE}/hotel-2",
        "api_key": "hotel-2-key-def456",
        "port": 8011,
        "description": "Hotel room reservations — search rooms, check availability, get pricing, book and cancel reservations",
    },
    "restaurant-1": {
        "name": "Restaurant 1",
        "base_url": f"{API_BASE}/restaurant-1",
        "api_key": "restaurant-1-key-ghi789",
        "port": 8012,
        "description": "Restaurant table reservations — find tables, check time slots, book and cancel",
    },
    "restaurant-2": {
        "name": "Restaurant 2",
        "base_url": f"{API_BASE}/restaurant-2",
        "api_key": "restaurant-2-key-jkl012",
        "port": 8013,
        "description": "Restaurant table reservations — find tables, check time slots, book and cancel",
    },
    "restaurant-3": {
        "name": "Restaurant 3",
        "base_url": f"{API_BASE}/restaurant-3",
        "api_key": "restaurant-3-key-mno345",
        "port": 8014,
        "description": "Restaurant table reservations — find tables, check time slots, book and cancel",
    },
    "flight-1": {
        "name": "SkyMock Air",
        "base_url": f"{API_BASE}/flight-1",
        "api_key": "flight-1-key-pqr678",
        "port": 8015,
        "description": "Flight bookings — search flights across 6 US cities, 3 seat classes, pricing and booking",
    },
    "car-rental-1": {
        "name": "Car Rental",
        "base_url": f"{API_BASE}/car-rental-1",
        "api_key": "car-rental-1-key-stu901",
        "port": 8016,
        "description": "Car rentals — browse 16-vehicle fleet, 7 categories, date-range availability, book and cancel",
    },
    "tour-guide-1": {
        "name": "Tour Guide",
        "base_url": f"{API_BASE}/tour-guide-1",
        "api_key": "tour-guide-1-key-vwx234",
        "port": 8017,
        "description": "Tour bookings — 12 tours, 6 categories, difficulty levels, group limits, per-person pricing",
    },
    "museum-1": {
        "name": "Museum",
        "base_url": f"{API_BASE}/museum-1",
        "api_key": "museum-1-key-yza567",
        "port": 8018,
        "description": "Museum timed-entry tickets — 4 time slots, 4 ticket types (adult/child/senior/student), capacity limits",
    },
}
