# Implementation Plan: Property Management Dashboard

## Overview

Implement a Flutter Web property management dashboard with Firebase Firestore integration. The system provides two main views—Reservations and Inventory—connected through a NavigationRail with IndexedStack-based view preservation. A service layer abstracts Firestore interactions. Property-based tests validate correctness properties from the design.

## Tasks

- [x] 1. Set up project structure and dependencies
  - [x] 1.1 Configure pubspec.yaml with required dependencies
    - Add `firebase_core`, `cloud_firestore` dependencies
    - Add `dart_check` (or `glados`) as a dev dependency for property-based testing
    - Ensure Flutter SDK constraint is set for web support
    - _Requirements: 7.1_

  - [x] 1.2 Create directory structure and placeholder files
    - Create `lib/models/`, `lib/services/`, `lib/views/`, `lib/widgets/` directories
    - Create `test/models/`, `test/services/`, `test/validation/`, `test/views/`, `test/widgets/`, `test/properties/` directories
    - _Requirements: 7.1_

- [x] 2. Implement data models
  - [x] 2.1 Implement Temple model
    - Create `lib/models/temple.dart` with fields: `id`, `templeName`, `totalCapacity`, `availableRooms`
    - Add `bookedRooms` getter using `(totalCapacity - availableRooms).clamp(0, totalCapacity)`
    - Add `factory Temple.fromMap(String id, Map<String, dynamic> map)` constructor
    - Add `Map<String, dynamic> toMap()` method with snake_case keys
    - All fields must have explicit Dart types (no dynamic)
    - _Requirements: 4.3, 7.2, 7.3_

  - [x] 2.2 Implement Reservation model
    - Create `lib/models/reservation.dart` with fields: `id`, `customerName`, `customerPhone`, `createdAt`
    - Add `factory Reservation.fromMap(String id, Map<String, dynamic> map)` constructor reading snake_case fields
    - Add `Map<String, dynamic> toMap()` method with snake_case keys, using `FieldValue.serverTimestamp()` for `created_at`
    - All fields must have explicit Dart types (no dynamic)
    - _Requirements: 7.2, 7.3_

  - [ ]* 2.3 Write property test for model serialization round-trip
    - **Property 5: Model serialization round-trip preserves data**
    - Generate random Temple instances; verify `Temple.fromMap(id, temple.toMap())` equals original
    - Generate random Reservation instances; verify `Reservation.fromMap(id, reservation.toMap())` preserves `customerName` and `customerPhone`
    - Verify all keys in `toMap()` output are snake_case strings
    - Minimum 100 iterations
    - **Validates: Requirements 7.2**

- [ ] 3. Implement service layer
  - [x] 3.1 Create FirestoreServiceException class
    - Create `lib/services/firestore_service.dart`
    - Implement `FirestoreServiceException` with `message` and optional `originalError` fields
    - Implements `Exception` interface with `toString()` override
    - _Requirements: 1.3, 2.4, 4.6, 5.5, 6.5_

  - [x] 3.2 Implement FirestoreService with streams and write operations
    - Implement `Stream<List<Reservation>> getReservationsStream()` — ordered by `created_at` descending
    - Implement `Stream<List<Temple>> getTemplesStream()` — ordered by `temple_name` ascending
    - Implement `Future<void> addReservation(Reservation reservation)` — creates document in `reservations` collection
    - Implement `Future<void> updateTemple(String documentId, {required int totalCapacity, required int availableRooms})` — updates temple document
    - Wrap Firestore exceptions in `FirestoreServiceException`
    - Preserve snake_case field names in all reads and writes
    - _Requirements: 2.1, 2.3, 4.1, 4.4, 4.7, 5.2, 6.2, 7.3, 7.5_

- [x] 4. Implement main entry point with Firebase initialization
  - [x] 4.1 Create main.dart with Firebase init and error handling
    - Initialize Firebase with web-specific `FirebaseOptions` (apiKey, authDomain, projectId, storageBucket, messagingSenderId, appId)
    - Apply 10-second timeout using `.timeout(const Duration(seconds: 10))`
    - On success: run `DashboardApp`
    - On `TimeoutException`: run `ErrorApp` with timeout message
    - On other exceptions: run `ErrorApp` with error type description
    - Create `DashboardApp` widget with Material 3 theming (`useMaterial3: true`)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 7.4_

- [x] 5. Checkpoint - Verify project builds
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement DashboardShell with navigation
  - [x] 6.1 Create DashboardShell with NavigationRail and IndexedStack
    - Create `lib/views/dashboard_shell.dart`
    - Implement `NavigationRail` with two destinations: Reservations and Inventory
    - Use `IndexedStack` as the body to preserve view state across navigation
    - Only selected view is visible; inactive views retain state in memory
    - Navigation switch should be immediate (< 500ms perceived)
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 7. Implement ReservationsView
  - [x] 7.1 Create ReservationsView with StreamBuilder and real-time data
    - Create `lib/views/reservations_view.dart`
    - Use `StreamBuilder<List<Reservation>>` consuming `FirestoreService.getReservationsStream()`
    - Display `customer_name` and `customer_phone` for each reservation
    - Show loading indicator while stream has no data
    - Show error message with retry button on stream error
    - Show empty-state message when collection has no documents
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 7.5_

  - [x] 7.2 Implement search/filter functionality
    - Add text input field with 100-character maximum length
    - Filter reservations client-side on each keystroke (no debounce)
    - Case-insensitive substring match on `customer_name` OR `customer_phone`
    - Show empty-state message when filter matches zero results
    - Clearing search field restores full list
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 7.3 Write property test for search filter
    - **Property 1: Search filter includes only matching results**
    - Generate lists of 0–50 Reservation objects with random names/phones
    - Generate random query strings of length 0–20
    - Assert filtered result contains exactly those reservations where name or phone contains query (case-insensitive)
    - Minimum 100 iterations
    - **Validates: Requirements 3.2, 3.3, 3.4**

- [x] 8. Implement InventoryView
  - [x] 8.1 Create InventoryView with tabular display and real-time stream
    - Create `lib/views/inventory_view.dart`
    - Use `StreamBuilder<List<Temple>>` consuming `FirestoreService.getTemplesStream()`
    - Display tabular list with columns: `temple_name`, `total_capacity`, `available_rooms`, `booked_rooms`
    - Calculate and display `bookedRooms` using the model getter (min 0)
    - Show loading indicator, error message with retry, and empty-state message
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 7.5_

  - [ ]* 8.2 Write property test for booked rooms calculation
    - **Property 2: Booked rooms calculation is non-negative and correct**
    - Generate random int pairs (0–100000) for capacity/available
    - Assert `bookedRooms == max(0, totalCapacity - availableRooms)` and `bookedRooms >= 0`
    - Minimum 100 iterations
    - **Validates: Requirements 4.3**

- [x] 9. Implement UpdateInventoryDialog
  - [x] 9.1 Create UpdateInventoryDialog with validation and Firestore update
    - Create `lib/widgets/update_inventory_dialog.dart`
    - Pre-populate fields with current `total_capacity` and `available_rooms` values
    - Validate: both fields are integers in range [1, 10000], `available_rooms` ≤ `total_capacity`
    - Display inline validation error messages per field on invalid input
    - Prevent submission when validation fails
    - On valid submit: call `FirestoreService.updateTemple()` and close dialog
    - On service failure: show error message, retain form values, keep dialog open
    - On cancel: close dialog without modifying Firestore
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 7.5_

  - [ ]* 9.2 Write property test for inventory validation
    - **Property 3: Inventory update validation is sound and complete**
    - Generate random integer pairs (including negatives, zero, boundary values 1/10000/10001)
    - Assert validation accepts if and only if both in [1, 10000] and `availableRooms` ≤ `totalCapacity`
    - Assert all invalid inputs produce appropriate error messages
    - Minimum 100 iterations
    - **Validates: Requirements 5.2, 5.3**

- [x] 10. Implement AddWalkInGuestModal
  - [x] 10.1 Create AddWalkInGuestModal with validation and Firestore write
    - Create `lib/widgets/add_walk_in_guest_modal.dart`
    - Input fields: `customer_name` (max 100 chars), `customer_phone` (max 20 chars)
    - Validate: `customer_name` non-empty after trim, `customer_phone` non-empty and matches `^\+?[\d\s\-]+$`
    - Display inline validation error messages indicating which field is invalid
    - Prevent submission when validation fails
    - On valid submit: call `FirestoreService.addReservation()` and close modal
    - On service failure: show error message, retain form data, keep modal open
    - On cancel/close: close modal without creating a document
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.5_

  - [ ]* 10.2 Write property test for walk-in guest validation
    - **Property 4: Walk-in guest validation is sound and complete**
    - Generate random strings including empty, whitespace-only, valid phone patterns, invalid characters, boundary lengths (0, 100, 101 for name; 0, 20, 21 for phone)
    - Assert validation accepts if and only if name is non-empty (trimmed) ≤ 100 chars and phone is non-empty ≤ 20 chars matching `^\+?[\d\s\-]+$`
    - Minimum 100 iterations
    - **Validates: Requirements 6.2, 6.3**

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design
- Unit tests validate specific examples and edge cases
- All Firestore field names use snake_case — no camelCase transformation
- The service layer is the exclusive Firestore access point for views and widgets
- Use `dart_check` or `glados` library for property-based tests with minimum 100 iterations per property

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "2.2"] },
    { "id": 2, "tasks": ["2.3", "3.1"] },
    { "id": 3, "tasks": ["3.2"] },
    { "id": 4, "tasks": ["4.1"] },
    { "id": 5, "tasks": ["6.1"] },
    { "id": 6, "tasks": ["7.1", "8.1"] },
    { "id": 7, "tasks": ["7.2", "8.2", "9.1", "10.1"] },
    { "id": 8, "tasks": ["7.3", "9.2", "10.2"] }
  ]
}
```
