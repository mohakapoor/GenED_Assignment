<!--
Fill this in and submit it alongside your code. Answer in your own words —
these are the questions we'll also ask you about in the follow-up
conversation, so they should match what your code actually does.
-->

# Writeup

## 1. Mastery scoring

Intially while designing the architecture I started with a simple 10 for correct -2 for incorrect rule and enforced that the values stay between 0-100. 

Then I switched to an Exponetial Moving Average to Calculate Mastery, for every attempt I gave either 100 (correct) or 0 (incorrect) and it is calculated using:

new_score = (attempt_score * alpha) + (current_score * (1 - alpha))

I left alpha to be configurable in config.py as per need be.
Advantages:
1. No need to store the complete attempt history 
2. Smoothly approaches 100 asymptotically.

Disadvantages:
1. Treats every attempt the same
2. No Time Decay

## 2. The flaky AI dependency

I have treated the AI feedback dependency as non critical to the attempt. Attempt, mastery update and notfication is commited before even calling get_ai_feedback(), because I don't want a slow call to hold my SQL connection as it will affect rest of the Students.

If it is slow student waits for the feedback, if it raises AIFeedbackError, endpoint catches the exception and returns a fallback message, while the attempt and mastery are safe and committed to DB.

## 3. The crash-durability requirement

Step by step:
1. The attempt endpoint is called, it calculates the new score and saves it into the mastery table.
2. If the server crashes before or during the INSERT INTO notifications query.
3. Because all DB queries are warpped in the get_db() FastAPI dependency, the crash get intercepted.
4. It htis the Exception block and executes conn.rollback().
5. The mastery update and the attempts insert are intstantly reverted.

This makes the attempt, mastery update, and notification atomic: either all are committed or none are committed.



## 4. Rate limiting

It queries the attempts database table directly. It runs a SELECT COUNT(*) for that student where attempted_at is within the last 24 hours. I have made a db index on (student_id, attempted_at) to make sure it is fast.

On Boundary like at attempt number the 30 the COUNT(*) would return 29 the check will pass and attempt will be processed.

At attempt 31 the COUNT(*) will return 30. IT halts the process and throws 429 error.

This rate check is implemented after Valdiation so entering bad or wrong skill id wont count in attempts.

## 5. If you had another 3 days

I could move the get_ai_feedback call out of the HTTP endpoint to maybe a background queue.
I could use websockets to send the feedback to frontend so user doesnt have to wait.
I could write proper Test isolation.

## 6. Least confident about

I am least confident about the testing scripts, to keep it simple i just made another test DB to run tests on.
One flaw would be the tests could bleed into each other therefore i used different student ID for different tests.

For example, my rate-limit test inserts 30 attempts for student-mei. If the next test also uses student-mei, it will instantly fail with a 429 Too Many Requests error



## 7. AI tool use


I wrote teh code using an agentic IDE, I had to keep it focused and iterative instead of building everything in one go.
It built uneceesariliy complex testing structure which was not needed so I dropped it tried to write a simpler one.
It was useful for genertic boiler plate code like pydantic Models


