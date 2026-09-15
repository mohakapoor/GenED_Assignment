# GenEd Mastery Service — Design Specification

This document provides a comprehensive overview of the system architecture, abstractions, database schema, and endpoint workflows.

## 1. System Overview & Abstractions

The service follows a modular **Controller-Service-Repository** pattern adapted for a lightweight FastAPI application.

### Directory Structure & Responsibilities
- **`main.py` (Controller/Router)**: 
  - Purely responsible for HTTP routing and dependency injection.
  - Exposes the endpoints and enforces top-level security (Auth Bearer tokens).
  - Delegates all business logic to `endpoints.py`.
- **`endpoints.py` (Service Layer)**:
  - Houses the core business logic and database orchestration (e.g., `process_attempt`).
  - Handles fetching data, computing mastery math, inserting DB records, and returning Pydantic responses.
- **`database.py` (Repository/Infra)**:
  - Manages SQLite connection setup and teardown.
  - Provides the `get_db()` dependency which guarantees a strict transactional scope (commits on success, rolls back on exception).
- **`utils.py` (Helpers)**:
  - Contains reusable utilities such as authorization checkers (`verify_access`, `verify_student_only_access`) and math formulas (`calculate_new_mastery`).
- **`models.py` (Schemas)**:
  - Defines the Pydantic data structures for robust request validation and response formatting.
- **`seed_data.py` (Configuration)**:
  - Acts as the source of truth for mock tokens, teacher rosters, and skill IDs.
- **`ai_feedback.py` (External Integrations)**:
  - Stubs out the slow LLM generation required for returning attempt feedback.

## 2. API Endpoints & Workflows

### `POST /students/{student_id}/attempts`
**Purpose**: Submits a new learning attempt for a student.
**Workflow (`process_attempt`)**:
1. **Auth Verification**: Uses `verify_student_only_access` to ensure the caller is a STUDENT and their ID matches the URL.
2. **Skill Validation**: Checks if the requested `skill_id` exists in `SKILL_IDS`. Returns 400 immediately if invalid.
3. **Rate Limiting**: Checks if the student has >= 30 attempts in the rolling 24 hours (queries attempts table) and returns 429 if so. Executed after skill validation so bad inputs don't count.
3. **Mastery Fetch**: Queries the `mastery` table to get the student's current score (defaults to 0.0).
4. **Mastery Calculation**: Computes the new score via `calculate_new_mastery`.
5. **Ledger Insert**: Saves the attempt into the `attempts` table.
6. **Mastery Upsert**: Uses `ON CONFLICT DO UPDATE` to save the new score into the `mastery` table.
7. *(Pending)* **Milestones**: Check if score crossed an 80+ threshold and insert into `notifications`.
8. **Feedback**: Call `ai_feedback.py` in the background (gracefully falling back if it fails).

### `GET /students/{student_id}/mastery`
**Purpose**: Retrieves all current mastery scores for a specific student.
**Workflow**: Uses `verify_access` (Teachers and Students allowed) and queries the `mastery` table. Returns data wrapped in a `MasteryResponse` envelope pattern (`{"status": "...", "data": [...]}`). If no records exist, it returns an empty array with `"records not found"` status rather than a 404, representing a valid student with no data yet.

### `GET /notifications/{student_id}`
**Purpose**: Retrieves all milestone notifications for a student.
**Workflow**: Uses `verify_access` and queries the `notifications` table. Returns data wrapped in a `NotificationResponse` envelope pattern.

### Utility Endpoints
- `GET /health` & `GET /api_name`: Basic connectivity checks.
- `GET /identity`: Resolves the provided Bearer token into a `{role, user_id}` identity.
- `GET /has_access/{student_id}`: Test endpoint to explicitly verify role-based access control rules.

## 3. Database Architecture

- **Transactional Scope**: All database interactions via the `get_db()` dependency operate within a strict transactional scope using FastAPI's native generator dependency injection. The generator yields the connection, automatically committing on success and rolling back if FastAPI throws an exception. This guarantees the atomic integrity of multi-step operations (e.g., updating mastery and recording a notification).
- **Upserts**: Updating the `mastery` table leverages SQLite's native `INSERT ... ON CONFLICT DO UPDATE`. This safely creates or updates a student's mastery score in a single atomic query without deleting the underlying row history.

## 4. Authorization & Security

- **Role-Based Access Control**: Enforced via FastAPI dependencies (`verify_access`). Students can only access their own `student_id`, while Teachers can access any `student_id` present in their assigned roster.
- **Strict Write Access**: The `POST /attempts` endpoint is protected by a secondary `verify_student_only_access` dependency that explicitly prevents teachers from submitting attempts on a student's behalf.
- **Anti-Enumeration**: Invalid or unassigned `student_id` requests yield a generic `403 Forbidden` rather than a `404 Not Found` to prevent attackers from mapping valid student IDs.

## 5. Database Schema

The service uses SQLite for persistence. Dimension tables (`students` and `skills`) are pre-populated using the `seed_db()` script based on `seed_data.py`.

### 1. `teachers`, `students`, `skills`
Simple dimension tables with an `id TEXT PRIMARY KEY`.

### 2. `mastery`
Stores the current mastery score.
| Column | Type | Constraints |
| :--- | :--- | :--- |
| `student_id` | `TEXT` | `PRIMARY KEY, NOT NULL` |
| `skill_id` | `TEXT` | `PRIMARY KEY, NOT NULL` |
| `score` | `REAL` | `NOT NULL, DEFAULT 0.0, CHECK(0-100)` |
*(Composite PK on `student_id` and `skill_id`)*

### 3. `attempts`
Ledger of every attempt. Used for historical tracking and rate-limiting.
| Column | Type | Constraints |
| :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT`|
| `student_id` | `TEXT` | `NOT NULL` |
| `skill_id` | `TEXT` | `NOT NULL` |
| `is_correct` | `BOOLEAN` | `NOT NULL` |
| `attempted_at`| `INTEGER` | `DEFAULT (cast(strftime('%s','now') as int))` |
*(Includes index `idx_attempts_student_time` on `(student_id, attempted_at)` to optimize rate limits.)*

### 4. `notifications`
Durably records when a student crosses a mastery threshold.
| Column | Type | Constraints |
| :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT`|
| `student_id` | `TEXT` | `NOT NULL` |
| `skill_id` | `TEXT` | `NOT NULL` |
| `milestone` | `INTEGER` | `NOT NULL` (e.g. 80) |
| `created_at` | `INTEGER` | `DEFAULT (cast(strftime('%s','now') as int))` |
*(Includes a `UNIQUE` constraint on `(student_id, skill_id, milestone)` to prevent duplicate milestone triggers.)*

## 6. API Data Models

Pydantic schemas used to define and validate API shapes:
- **`AttemptRequest`**: Incoming payload (`skill_id`, `is_correct`).
- **`AttemptResponse`**: Outgoing result (`new_score`, `feedback`).
- **`MasteryItem`**: Core structure for a single skill's mastery (`skill_id`, `score`).
- **`MasteryResponse`**: Envelope wrapper for returning a list of `MasteryItem` objects (`status`, `data`).
- **`NotificationItem`**: Core structure for milestone alerts (`id`, `skill_id`, `milestone`, `created_at`).
- **`NotificationResponse`**: Envelope wrapper for returning a list of `NotificationItem` objects (`status`, `data`).
