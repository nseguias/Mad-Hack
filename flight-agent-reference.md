# SkyMock Air — Flight Reservation API — Agent Reference

You are interacting with a **Flight Reservation API** for the fictional airline **SkyMock Air**. It manages flights between US cities, seat availability, class-based pricing, and bookings.

## Authentication

All `/api/*` endpoints require an API key. Provide it via:

- **Header (recommended):** `X-API-Key: <key>`
- **Query parameter:** `?api_key=<key>`

Without a valid key, all API calls return `401`.

## Base URL

- **Behind gateway:** `https://hacketon-18march-api.orcaplatform.ai/<instance>/api/` (e.g. `/flight-1/api/`)
- **Standalone:** `/api/` on the host/port where that standalone service is running

## Typical Workflow

1. Call `GET /api/destinations` to see all served cities
2. Call `GET /api/flights/search` with origin and destination to find available flights
3. Call `GET /api/pricing` to get a price quote for a flight + seat class
4. Call `POST /api/bookings` to book
5. Call `GET /api/bookings` to list bookings
6. Call `DELETE /api/bookings/{id}` to cancel if needed

---

## Seat Classes & Pricing

| Class | Multiplier | Example ($199 base) |
|-------|-----------|---------------------|
| economy | 1.0x | $199.00 |
| business | 2.5x | $497.50 |
| first | 5.0x | $995.00 |

Price = `base_price * class_multiplier * num_passengers`

---

## Endpoints

### GET /api/schema

Returns a machine-readable manifest describing all endpoints. No parameters.

### GET /api/health

Returns `{"status": "ok", "airline": "SkyMock Air"}`.

---

### GET /api/destinations

List all cities served.

**Response:** `200 OK`

```json
{
  "cities": ["Chicago", "Denver", "Los Angeles", "Miami", "New York", "Seattle"]
}
```

---

### GET /api/flights

List all flights, optionally filtered.

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| origin | string | No | Filter by departure city (partial match) |
| destination | string | No | Filter by arrival city (partial match) |
| date | date (YYYY-MM-DD) | No | Filter by departure date |

**Response:** `200 OK` — Array of flight objects

```json
[
  {
    "id": 1,
    "flight_number": "SM101",
    "origin": "New York",
    "destination": "Los Angeles",
    "departure_date": "2026-03-10",
    "departure_time": "08:00",
    "arrival_time": "11:30",
    "total_seats": 180,
    "available_seats": 180,
    "base_price": 199.0,
    "status": "scheduled"
  }
]
```

---

### GET /api/flights/search

Search for available flights with enough seats.

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| origin | string | Yes | Departure city (partial match) |
| destination | string | Yes | Arrival city (partial match) |
| date | date (YYYY-MM-DD) | No | Filter by departure date |
| passengers | integer (>= 1) | No | Minimum available seats required |

**Response:** `200 OK` — Array of flight objects (only `scheduled` flights with enough seats)

---

### GET /api/flights/{id}

Get details of a specific flight.

**Response:** `200 OK` — Flight object

**Errors:**
- `404` — Flight not found

---

### GET /api/pricing

Get a price quote.

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| flight_id | integer | Yes | Flight ID |
| seat_class | string | No | `economy` (default), `business`, or `first` |
| passengers | integer (>= 1) | No | Number of passengers (default: 1) |

**Response:** `200 OK`

```json
{
  "flight_id": 1,
  "flight_number": "SM101",
  "origin": "New York",
  "destination": "Los Angeles",
  "departure_date": "2026-03-10",
  "seat_class": "business",
  "base_price": 199.0,
  "class_multiplier": 2.5,
  "price_per_passenger": 497.5,
  "num_passengers": 2,
  "total_price": 995.0
}
```

**Errors:**
- `400` — Invalid seat class
- `404` — Flight not found

---

### POST /api/bookings

Create a new booking. Decrements available seats on the flight.

**Request body (JSON):**

```json
{
  "flight_id": 1,
  "passenger_name": "Jane Doe",
  "passenger_email": "jane@example.com",
  "num_passengers": 2,
  "seat_class": "economy"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| flight_id | integer | Yes | Flight ID |
| passenger_name | string | Yes | Passenger's full name |
| passenger_email | string | Yes | Passenger's email |
| num_passengers | integer (>= 1) | Yes | Number of passengers |
| seat_class | string | No | `economy` (default), `business`, or `first` |

**Response:** `201 Created`

```json
{
  "id": 1,
  "flight_id": 1,
  "flight_number": "SM101",
  "origin": "New York",
  "destination": "Los Angeles",
  "departure_date": "2026-03-10",
  "departure_time": "08:00",
  "passenger_name": "Jane Doe",
  "passenger_email": "jane@example.com",
  "num_passengers": 2,
  "seat_class": "economy",
  "total_price": 398.0,
  "status": "confirmed",
  "created_at": "2026-03-07T12:00:00"
}
```

**Errors:**
- `400` — Invalid seat class, or flight is not `scheduled`
- `404` — Flight not found
- `409` — Not enough available seats

---

### GET /api/bookings

List all bookings.

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| status | string | No | Filter by status: `confirmed` or `cancelled` |

**Response:** `200 OK` — Array of booking objects (same shape as POST response)

---

### GET /api/bookings/{id}

Get a single booking by ID.

**Response:** `200 OK` — Booking object

**Errors:**
- `404` — Booking not found

---

### DELETE /api/bookings/{id}

Cancel a booking. Sets status to `cancelled` and restores available seats on the flight.

**Response:** `200 OK` — Updated booking object with `"status": "cancelled"`

**Errors:**
- `400` — Booking is already cancelled
- `404` — Booking not found

---

## Seed Data (Available Flights)

| ID | Flight # | Origin | Destination | Date | Depart | Arrive | Seats | Base Price |
|----|----------|--------|-------------|------|--------|--------|-------|-----------|
| 1 | SM101 | New York | Los Angeles | 2026-03-10 | 08:00 | 11:30 | 180 | $199 |
| 2 | SM102 | Los Angeles | New York | 2026-03-10 | 14:00 | 22:15 | 180 | $209 |
| 3 | SM201 | New York | Chicago | 2026-03-11 | 07:30 | 09:45 | 150 | $129 |
| 4 | SM202 | Chicago | New York | 2026-03-11 | 16:00 | 20:10 | 150 | $139 |
| 5 | SM301 | Chicago | Miami | 2026-03-12 | 09:00 | 13:15 | 160 | $179 |
| 6 | SM302 | Miami | Chicago | 2026-03-12 | 15:30 | 19:40 | 160 | $169 |
| 7 | SM401 | Los Angeles | Seattle | 2026-03-13 | 06:45 | 09:15 | 140 | $99 |
| 8 | SM402 | Seattle | Los Angeles | 2026-03-13 | 17:00 | 19:30 | 140 | $109 |
| 9 | SM501 | Miami | Denver | 2026-03-14 | 10:00 | 13:00 | 120 | $189 |
| 10 | SM502 | Denver | Miami | 2026-03-14 | 14:30 | 20:30 | 120 | $199 |
| 11 | SM601 | Seattle | Denver | 2026-03-15 | 08:00 | 11:30 | 130 | $149 |
| 12 | SM602 | Denver | Seattle | 2026-03-15 | 13:00 | 15:00 | 130 | $139 |
| 13 | SM701 | New York | Miami | 2026-03-16 | 06:00 | 09:15 | 180 | $159 |
| 14 | SM702 | Miami | New York | 2026-03-16 | 18:00 | 21:15 | 180 | $169 |
| 15 | SM801 | Los Angeles | Denver | 2026-03-17 | 11:00 | 14:00 | 150 | $119 |

## Error Response Format

All errors return JSON:

```json
{
  "detail": "Human-readable error message"
}
```

Common HTTP status codes: `400` (bad request), `401` (unauthorized), `404` (not found), `409` (conflict).
