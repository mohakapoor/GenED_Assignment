<!--
Fill this in and submit it alongside your code. Answer in your own words —
these are the questions we'll also ask you about in the follow-up
conversation, so they should match what your code actually does.
-->

# Writeup

## 1. Mastery scoring

Initially while designing the architecture I started with a simple 10 for correct -2 for incorrect rule and enforced that the values stay between 0-100. 

Then I switched to an Exponential Moving Average to calculate mastery, for every attempt I gave either 100 (correct) or 0 (incorrect) and it is calculated using:

new_score = (attempt_score * alpha) + (current_score * (1 - alpha))

I left alpha to be configurable in config.py as per need be.
Advantages:
1. No need to store the complete attempt history 
2. Smoothly approaches 100 asymptotically.

Disadvantages:
1. Treats every attempt the same
2. No Time Decay

## 2. The flaky AI dependency

I have treated the AI feedback dependency as non critical to the attempt. Attempt, mastery update and notification is committed before even calling get_ai_feedback(), because I don't want a slow call to hold my SQL connection as it will affect rest of the Students.

If it is slow student waits for the feedback, if it raises AIFeedbackError, endpoint catches the exception and returns a fallback message, while the attempt and mastery are safe and committed to DB.

## 3. The crash-durability requirement

Step by step:
1. The attempt endpoint is called, it calculates the new score and saves it into the mastery table.
2. The attempt insert, mastery upsert, and notification insert all happen inside a single SQLite transaction.
3. I call db.commit() explicitly only after all three writes are done, so they are atomic.
4. If the server crashes at any point before that commit, none of the writes are saved.
5. If the server crashes before that commit, my Python except block doesn't save me, a real crash like an OOM kill or power loss won't run any Python code at all.
6. What helps is SQLite itself, it keeps a journal of in-progress writes, and if a transaction was never committed, SQLite automatically discards it the next time anyone opens the database. So even without my code running, the data stays consistent.

The reason I commit explicitly inside the endpoint (before calling the AI) is so the slow get_ai_feedback() call doesn't hold my write transaction open for 0.5-5 seconds. By committing early, the student's data is safe and the database is free for other requests while we wait on the AI.



## 4. Rate limiting

It queries the attempts database table directly. It runs a SELECT COUNT(*) for that student where attempted_at is within the last 24 hours. I have made a db index on (student_id, attempted_at) to make sure it is fast.

On the boundary, like at attempt number 30 the COUNT(*) would return 29, the check will pass and the attempt will be processed.

At attempt 31 the COUNT(*) will return 30. It halts the process and throws 429 error.

This rate check is implemented after validation so entering bad or wrong skill id won't count in attempts.
One concern is concurrency, two requests could both pass the rate check before either inserts. SQLite's single-writer lock makes this unlikely, but in production I could try SELECT ... FOR UPDATE.


## 5. If you had another 3 days

I could move the get_ai_feedback call out of the HTTP endpoint to maybe a background queue.
I could use websockets to send the feedback to frontend so user doesn't have to wait.
I could write proper Test isolation.

## 6. Least confident about

I am least confident about the testing scripts, to keep it simple i just made another test DB to run tests on.
One flaw would be the tests could bleed into each other therefore i used different student ID for different tests.

For example, my rate-limit test inserts 30 attempts for student-mei. If the next test also uses student-mei, it will instantly fail with a 429 Too Many Requests error



## 7. AI tool use


I wrote the code using an agentic IDE, I had to keep it focused and iterative instead of building everything in one go.
It built unnecessarily complex testing structure which was not needed so I dropped it and tried to write a simpler one.
It was useful for generic boiler plate code like pydantic Models


