# GenEd Mastery Service — Take-Home Submission

I've finished the assignment. The service implements all three required endpoints (attempts, mastery, notifications) plus a teacher roster summary as a stretch goal. See `WRITEUP.md` for my design decisions and trade-offs.

Below is how to run it.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

First, initialize and seed the SQLite database with the mock data:
```bash
python -m mastery_service.database
```

Then, start the FastAPI server:
```bash
uvicorn mastery_service.main:app --reload
```

Then visit http://127.0.0.1:8000/docs for the Swagger UI.

## Test

```bash
pytest tests
```

## Documentation

- [`WRITEUP.md`](WRITEUP.md) — design decisions, trade-offs, and answers to the writeup questions
- [`docs/design.md`](docs/design.md) — full system design with workflow diagrams, ERD, and database schema
