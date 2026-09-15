# Design Specification

## Database Architecture

- **Transactional Scope**: All database interactions provided to the API routes via the `get_db()` dependency operate within a strict transactional scope using FastAPI's native generator dependency injection. The generator yields the connection, automatically committing on success and rolling back if FastAPI throws an exception back into the generator. This guarantees the atomic integrity of multi-step operations (like updating a mastery score and recording a milestone notification), ensuring the system is strictly crash-durable as required by the spec.

## Authorization & Security

- **Role-Based Access Control**: Enforced via FastAPI dependencies (`verify_access`). Students can only access their own `student_id`, while Teachers can access any `student_id` present in their assigned roster in `seed_data.py`.
- **Anti-Enumeration**: Invalid or unassigned `student_id` requests yield a generic `403 Forbidden` rather than a `404 Not Found` to prevent user enumeration attacks.

## Database Schema

The service uses SQLite for persistence. We enforce foreign keys to the dimension tables (`students` and `skills`) to ensure data integrity. These dimension tables are pre-populated using the `seed_db()` script based on the provided `seed_data.py`.

### 1. `teachers`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `TEXT` | `PRIMARY KEY` | Unique identifier for a teacher. |

### 2. `students`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `TEXT` | `PRIMARY KEY` | Unique identifier for a student. |

### 3. `skills`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `TEXT` | `PRIMARY KEY` | Unique identifier for a skill. |

### 4. `mastery`
Stores the current mastery score for a given student and skill.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `student_id` | `TEXT` | `PRIMARY KEY, NOT NULL` | The student's ID. |
| `skill_id` | `TEXT` | `PRIMARY KEY, NOT NULL` | The skill's ID. |
| `score` | `REAL` | `NOT NULL, DEFAULT 0.0, CHECK(0-100)` | Float used to prevent rounding truncation during moving average calculations. |

*(Composite Primary Key on `student_id` and `skill_id`)*

### 5. `attempts`
Ledger of every attempt made by a student. Used for historical tracking and enforcing the rate limit (30 attempts per 24 hours).

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT`| Unique identifier for the attempt. |
| `student_id` | `TEXT` | `NOT NULL` | The student who made the attempt. |
| `skill_id` | `TEXT` | `NOT NULL` | The skill attempted. |
| `is_correct` | `BOOLEAN` | `NOT NULL` | Whether the attempt was successful. |
| `attempted_at`| `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | When the attempt occurred. |

*(Includes a composite index `idx_attempts_student_time` on `(student_id, attempted_at)` to optimize 24-hour rate limiting queries.)*

### 6. `notifications`
Durably records when a student crosses a mastery threshold (e.g., score > 80) for the first time.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT`| Unique identifier for the notification. |
| `student_id` | `TEXT` | `NOT NULL` | The student who crossed the milestone. |
| `skill_id` | `TEXT` | `NOT NULL` | The skill the milestone was reached in. |
| `milestone` | `INTEGER` | `NOT NULL` | The exact threshold crossed (e.g., `80`). |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | When the milestone was recorded. |

*(Includes a `UNIQUE` constraint on `(student_id, skill_id, milestone)` to prevent duplicate notifications for the same threshold.)*

## API Endpoints

The service exposes the following core endpoints, protected by the `verify_access` dependency where applicable:

- `GET /health` & `GET /api_name`: Basic connectivity checks.
- `GET /identity`: Resolves the provided token into a `{role, user_id}` identity.
- `GET /has_access/{student_id}`: A test endpoint to explicitly verify role-based access control rules.
- `POST /students/{student_id}/attempts`: Submits a learning attempt, checks rate limits, calculates mastery, and triggers milestone notifications.
- `GET /students/{student_id}/mastery`: (Pending) Retrieves all current mastery scores for a specific student.
- `GET /notifications/{student_id}`: (Pending) Retrieves all milestone notifications triggered by a specific student.

## API Data Models

The service uses Pydantic schemas to define and validate the shapes of API requests and responses:

- **`AttemptRequest`**: Incoming payload for an attempt (`skill_id`, `is_correct`).
- **`AttemptResponse`**: Outgoing result of an attempt, including the calculated `new_score` and AI-generated `feedback`.
- **`MasteryItem`**: Outgoing payload for a single skill's mastery (`skill_id`, `score`).
- **`NotificationItem`**: Outgoing payload for milestone alerts (`id`, `skill_id`, `milestone`, `created_at`).
