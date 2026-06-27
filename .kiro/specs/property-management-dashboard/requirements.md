# Requirements Document

## Introduction

A Property Management System (PMS) dashboard built as a Flutter Web prototype integrated with Firebase Firestore. The system provides property managers with a centralized interface to view reservations, manage property inventory (temples), and add walk-in guest reservations. The dashboard uses Material 3 design principles and connects directly to Firestore collections using snake_case field naming.

## Glossary

- **Dashboard**: The main Flutter Web application providing an admin interface for property management operations
- **Reservations_View**: The primary view displaying current reservations retrieved from Firestore
- **Inventory_View**: The view displaying property (temple) information including capacity and availability
- **Update_Inventory_Dialog**: A modal dialog for modifying property capacity and availability values
- **Add_Walk_In_Guest_Modal**: A modal dialog for creating new reservation records
- **Firestore_Service**: The service layer responsible for all communication with Firebase Firestore
- **Temple**: A property entity stored in the `temples` Firestore collection
- **Reservation**: A booking record stored in the `reservations` Firestore collection
- **Booked_Rooms**: A calculated value derived from `total_capacity` minus `available_rooms`

## Requirements

### Requirement 1: Firebase Web Initialization

**User Story:** As a developer, I want the application to initialize Firebase for Flutter Web on startup, so that Firestore connectivity is available throughout the application lifecycle.

#### Acceptance Criteria

1. WHEN the Dashboard application starts, THE Dashboard SHALL initialize Firebase with web-specific configuration (FirebaseOptions with apiKey, authDomain, projectId, storageBucket, messagingSenderId, and appId) before rendering any UI components
2. WHEN Firebase initialization succeeds, THE Dashboard SHALL render the main UI within 5 seconds of application start
3. IF Firebase initialization fails, THEN THE Dashboard SHALL display an error message indicating the connection failure and the type of error encountered, instead of rendering the main UI
4. IF Firebase initialization has not completed within 10 seconds, THEN THE Dashboard SHALL treat the initialization as failed and display an error message indicating a timeout

### Requirement 2: Reservations Dashboard View

**User Story:** As a property manager, I want to view all current reservations in a high-level overview, so that I can monitor guest bookings at a glance.

#### Acceptance Criteria

1. WHEN the Reservations_View is loaded, THE Dashboard SHALL retrieve all documents from the `reservations` Firestore collection and display them in a list ordered by document creation time descending (newest first)
2. THE Reservations_View SHALL display `customer_name` and `customer_phone` for each reservation record
3. WHEN a new reservation document is added to Firestore, THE Reservations_View SHALL display the new record within 5 seconds of the document being committed, without requiring a manual page refresh
4. IF the Reservations_View fails to retrieve data from the `reservations` Firestore collection, THEN THE Dashboard SHALL display an error message indicating the data could not be loaded and provide an option to retry the retrieval
5. IF the `reservations` Firestore collection contains no documents, THEN THE Reservations_View SHALL display a message indicating that no reservations currently exist

### Requirement 3: Reservation Search and Filter

**User Story:** As a property manager, I want to search and filter reservations by customer name or phone number, so that I can locate specific bookings efficiently.

#### Acceptance Criteria

1. THE Reservations_View SHALL provide a text input field for entering search queries, with a maximum input length of 100 characters
2. WHEN the property manager enters at least 1 character in the search field, THE Reservations_View SHALL filter the displayed reservations in real time (on each keystroke) to show only records where `customer_name` or `customer_phone` contains the entered text as a substring (case-insensitive)
3. IF the search filter matches zero reservations, THEN THE Reservations_View SHALL display an empty-state message indicating that no reservations match the search query
4. WHEN the search field is cleared, THE Reservations_View SHALL display all reservations without filtering

### Requirement 4: Inventory Management View

**User Story:** As a property manager, I want to view all properties with their capacity details, so that I can understand current availability and occupancy.

#### Acceptance Criteria

1. WHEN the Inventory_View is loaded, THE Dashboard SHALL retrieve all documents from the `temples` Firestore collection and display them in a tabular list
2. THE Inventory_View SHALL display the following fields for each temple: `temple_name`, `total_capacity`, `available_rooms`, and Booked_Rooms
3. THE Inventory_View SHALL calculate Booked_Rooms as the value of `total_capacity` minus `available_rooms` for each temple, displaying a minimum value of 0 if `available_rooms` exceeds `total_capacity`
4. WHEN a temple document is updated in Firestore, THE Inventory_View SHALL reflect the changes within 5 seconds without requiring a manual page refresh
5. IF the `temples` Firestore collection contains no documents, THEN THE Inventory_View SHALL display a message indicating that no properties are available
6. IF the Firestore connection fails during data retrieval or real-time listening, THEN THE Inventory_View SHALL display an error message indicating the data could not be loaded and provide an option to retry
7. WHEN a temple document is added to or removed from the `temples` Firestore collection, THE Inventory_View SHALL update the displayed list within 5 seconds without requiring a manual page refresh

### Requirement 5: Update Inventory Dialog

**User Story:** As a property manager, I want to update the capacity and availability of a property through a modal dialog, so that I can reflect changes in room allocation.

#### Acceptance Criteria

1. WHEN the property manager selects a temple from the Inventory_View, THE Dashboard SHALL display the Update_Inventory_Dialog pre-populated with the current `total_capacity` and `available_rooms` values
2. WHEN the property manager submits values in the Update_Inventory_Dialog where both `total_capacity` and `available_rooms` are integers greater than or equal to 1 and less than or equal to 10,000, and `available_rooms` is less than or equal to `total_capacity`, THE Firestore_Service SHALL update the corresponding temple document in the `temples` collection with the new `total_capacity` and `available_rooms` values
3. IF the property manager enters a value that is not an integer, is less than 1, is greater than 10,000, or where `available_rooms` exceeds `total_capacity`, THEN THE Update_Inventory_Dialog SHALL display a validation error indicating the failing constraint and prevent submission
4. WHEN the property manager cancels the Update_Inventory_Dialog, THE Dashboard SHALL close the dialog without modifying Firestore data
5. IF the Firestore_Service fails to update the temple document after the property manager submits valid values, THEN THE Update_Inventory_Dialog SHALL display an error message indicating the update was unsuccessful and SHALL retain the entered values in the form

### Requirement 6: Add Walk-In Guest Modal

**User Story:** As a property manager, I want to add a walk-in guest reservation through a modal form, so that I can record bookings for guests who arrive without a prior reservation.

#### Acceptance Criteria

1. WHEN the property manager activates the add walk-in guest action, THE Dashboard SHALL display the Add_Walk_In_Guest_Modal with input fields for `customer_name` (maximum 100 characters) and `customer_phone` (maximum 20 characters)
2. WHEN the property manager submits the Add_Walk_In_Guest_Modal with a non-empty `customer_name` and a non-empty `customer_phone` containing only digits, spaces, hyphens, or a leading plus sign, THE Firestore_Service SHALL create a new document in the `reservations` collection with the provided `customer_name` and `customer_phone` values
3. IF `customer_name` or `customer_phone` is empty on submission, or `customer_phone` contains characters other than digits, spaces, hyphens, or a leading plus sign, THEN THE Add_Walk_In_Guest_Modal SHALL display an inline validation error message indicating which field is invalid and SHALL prevent submission
4. WHEN the reservation is created successfully, THE Add_Walk_In_Guest_Modal SHALL close and THE Reservations_View SHALL append the new reservation to the displayed list without requiring a manual refresh
5. IF the Firestore_Service fails to create the reservation document, THEN THE Add_Walk_In_Guest_Modal SHALL remain open, preserve the entered data, and display an error message indicating the reservation could not be saved
6. WHEN the property manager activates the cancel or close action on the Add_Walk_In_Guest_Modal, THE Add_Walk_In_Guest_Modal SHALL close without creating a reservation document

### Requirement 7: Application Architecture and Code Organization

**User Story:** As a developer, I want the codebase to follow a clean modular structure separating UI from service logic, so that the code is maintainable and testable.

#### Acceptance Criteria

1. THE Dashboard SHALL organize source code into at minimum four separate directories under lib/: models/ for data classes, services/ for Firestore interaction logic, views/ for screen-level widgets, and widgets/ for reusable UI components
2. THE Dashboard SHALL use Dart model classes for Temple and Reservation entities where every field has an explicit Dart type (no dynamic), and each model provides a factory constructor from a Firestore document map and a method that returns a Map<String, dynamic> with snake_case keys for writing to Firestore
3. THE Firestore_Service SHALL preserve snake_case field names when reading from and writing to Firestore documents without converting to camelCase
4. THE Dashboard SHALL enable Material 3 theming by setting useMaterial3: true in the application ThemeData configuration
5. THE Dashboard views and widgets SHALL access Firestore data exclusively through Firestore_Service classes, with no direct Firestore package imports in files under lib/views/ or lib/widgets/

### Requirement 8: Navigation Between Views

**User Story:** As a property manager, I want to navigate between the reservations overview and inventory management sections, so that I can access different parts of the system without losing context.

#### Acceptance Criteria

1. THE Dashboard SHALL provide a persistent navigation control visible on all views, allowing the property manager to switch between the Reservations_View and the Inventory_View with a single interaction
2. WHEN the property manager selects a navigation destination, THE Dashboard SHALL display the corresponding view within 500 milliseconds of the interaction
3. WHEN the property manager navigates from one view to another and then returns to the previous view, THE Dashboard SHALL restore that view's prior state including any active search filter text, selected filter options, sort order, and scroll position
4. WHILE a view is not actively displayed, THE Dashboard SHALL retain that view's state in memory until the user's session ends or the browser tab is closed
5. IF the Dashboard fails to load a requested view, THEN THE Dashboard SHALL continue displaying the current view and present an error message indicating the navigation could not be completed
