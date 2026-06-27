# 🏨 Temple PMS — Property Management System

A modern, real-time Property Management System built for temple accommodation management. This prototype demonstrates how a complete hotel operations dashboard can be paired with conversational AI booking channels (WhatsApp, Voice Assistant) to create a unified reservation platform.

---

## What This Project Does

Temple PMS manages room inventory and reservations across multiple temple hotels (Shirdi, Srisailam, Tirupati). It provides:

- **Live Dashboard** — KPI cards showing total rooms, availability, today's reservations, and booking source analytics, all updating in real time.
- **Reservation Management** — Full CRUD operations on reservations with status tracking, search, and filtering.
- **Inventory Control** — Per-temple room capacity management with maintenance room tracking and occupancy visualization.
- **Multi-Channel Booking** — Reservations flow in from WhatsApp (via Botpress), Voice Assistant, and manual Walk-In entries — all visible in one place.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Flutter Web (Material 3) |
| Backend | Firebase Firestore (real-time streams) |
| WhatsApp Bot | Botpress → Firestore REST API |
| Deployment | Flutter Web build, Firebase Hosting (optional) |

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  WhatsApp User  │────▶│     Botpress      │────▶│                     │
└─────────────────┘     └──────────────────┘     │                     │
                                                  │  Firebase Firestore │
┌─────────────────┐                               │                     │
│  Voice Assistant │──────────────────────────────▶│  • reservations     │
└─────────────────┘                               │  • temples          │
                                                  │                     │
┌─────────────────┐     ┌──────────────────┐     │                     │
│   Receptionist  │────▶│  Flutter Web App  │◀───▶│                     │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
                              (real-time)
```

---

## Features by Version

### v1.0 — Foundation
- Material 3 dashboard with sidebar navigation
- Real-time Firestore integration
- Reservation list with search
- Temple inventory display

### v1.1 — Dashboard KPIs
- Total Rooms, Available Rooms, Today's Reservations, Total Reservations
- All KPIs derived from Firestore streams

### v1.2 — Inventory Refactor
- Temple collection as single source of truth for availability
- Maintenance rooms tracking
- `Occupied = Total - Available - Maintenance`

### v1.3 — Reservation Intelligence
- Reservation Status (Waiting for Approval → Approved & Paid → Cancelled)
- Reservation Mode (WhatsApp Booking, Voice Assistant, Walk-In)
- Color-coded status chips with icons
- Extended multi-field search

### v1.3.1 — Booking Source Analytics
- Dashboard section showing bookings by channel
- WhatsApp, Voice Assistant, Walk-In, Total Digital counters

### v1.4 — Reservation Management
- Edit reservations (pre-populated dialog)
- Delete reservations (with confirmation)
- Reusable Add/Edit dialog component
- Status dropdown with controlled values

---

## Firestore Schema

### `temples` collection

```json
{
  "temple_name": "Srisailam",
  "total_capacity": 35,
  "available_rooms": 24,
  "maintenance_rooms": 1
}
```

### `reservations` collection

```json
{
  "customer_name": "Srikanth",
  "customer_phone": "9533335245",
  "customer_age": 28,
  "temple_name": "Srisailam",
  "room_type": "Double Cot with A/C",
  "check_in": "2026-06-26T00:00:00Z",
  "check_out": "2026-06-29T00:00:00Z",
  "no_of_rooms": 2,
  "reservation_status": "Approved & Paid",
  "reservation_mode": "WhatsApp Booking",
  "created_at": "2026-06-26T10:12:21.031Z"
}
```

---

## Getting Started

### Prerequisites

- Flutter SDK ≥ 3.16.0
- Dart SDK ≥ 3.2.0
- A Firebase project with Firestore enabled

### Run Locally

```bash
git clone <this-repo>
cd hotel-pms-proto
flutter pub get
flutter run -d chrome
```

### Export Firestore Data

```bash
node export_firestore.js
```

Saves `reservations.json` and `temples.json` to `firestore_export/`.

---

## Project Structure

```
lib/
├── main.dart                    # App entry, Firebase init, Material 3 theme
├── models/
│   ├── reservation.dart         # Reservation data model
│   └── temple.dart              # Temple data model
├── services/
│   └── firestore_service.dart   # All Firestore operations
├── views/
│   ├── dashboard_shell.dart     # Sidebar + AppBar shell
│   ├── dashboard_view.dart      # KPIs + Analytics + Temple cards
│   ├── reservations_view.dart   # Reservation list + Edit/Delete
│   └── inventory_view.dart      # Temple inventory management
└── widgets/
    ├── add_walk_in_guest_modal.dart  # Reusable Add/Edit reservation dialog
    └── update_inventory_dialog.dart  # Temple inventory update dialog
```

---

## WhatsApp Integration

The Botpress chatbot connects to Firestore via REST API. It:

1. Collects guest details (name, phone, dates, rooms)
2. Checks availability against temple capacity
3. Creates reservation documents directly in Firestore
4. Dashboard reflects new bookings instantly

See `functions/index.js` for the Cloud Functions implementation (requires Blaze plan) or use the Firestore REST API approach directly from Botpress (works on Spark/free plan).

---

## License

This is a prototype project built for demonstration purposes.

---

Built with Flutter, Firebase, and Botpress.
