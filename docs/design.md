# Design Specification

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
| `student_id` | `TEXT` | `PRIMARY KEY` | The student's ID. |
| `skill_id` | `TEXT` | `PRIMARY KEY` | The skill's ID. |
| `score` | `REAL` | | Float used to prevent rounding truncation during moving average calculations. |

*(Composite Primary Key on `student_id` and `skill_id`)*

### 5. `attempts`
Ledger of every attempt made by a student. Used for historical tracking and enforcing the rate limit (30 attempts per 24 hours).

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT`| Unique identifier for the attempt. |
| `student_id` | `TEXT` | | The student who made the attempt. |
| `skill_id` | `TEXT` | | The skill attempted. |
| `is_correct` | `BOOLEAN` | | Whether the attempt was successful. |
| `attempted_at`| `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | When the attempt occurred. |

*(Includes a composite index `idx_attempts_student_time` on `(student_id, attempted_at)` to optimize 24-hour rate limiting queries.)*

### 6. `notifications`
Durably records when a student crosses a mastery threshold (e.g., score > 80) for the first time.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT`| Unique identifier for the notification. |
| `student_id` | `TEXT` | | The student who crossed the milestone. |
| `skill_id` | `TEXT` | | The skill the milestone was reached in. |
| `milestone` | `INTEGER` | | The exact threshold crossed (e.g., `80`). |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | When the milestone was recorded. |
