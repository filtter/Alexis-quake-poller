Resilient Data Poller + Dashboard



This project is a long-lived service that polls the USGS earthquake API every 60 seconds, stores the data idempotently in SQLite, and exposes it on a basic HTML dashboard.







How to Run:



1. Install Python 3.13+.
2. Install the network dependency:

   * **pip install request**
3. Run the poller in one terminal:

   * **python poller.py**
4. Run the dashboard in another terminal:

   * **python server.py**
5. Open your browser at **http://localhost:8000**





Key Design Decisions:



1. Database-level Idempotency: Instead of doing a SELECT to check if a record exists before inserting it, we use the USGS GeoJSON id field as the Primary Key (Natural Key). We use SQLite's INSERT OR IGNORE clause. If the poller queries the same hour twice, the database simply ignores duplicates without throwing errors or overloading the CPU.
2. Extreme Resilience: The main poller loop is designed under the "fail safely" principle.Use of timeout=(10, 15) to prevent the script from hanging forever waiting for a response.Use of raise\_for\_status() to catch non-200 HTTP codes before attempting to parse garbage.Granular exception handling: network errors don't abort the process, and errors in an individual record don't abort the rest of the batch.
3. No Backend Frameworks: Python's standard http.server library was used for the dashboard. The PDF specified "no framework you don't need". To serve a static HTML table, Flask or FastAPI are overkill. This keeps the system lightweight with zero external dependencies beyond requests.



What Was Intentionally Left Out



**UI/UX Design:** Pure text-style HTML was chosen.

**Authentication:** Unnecessary for public read-only data.

**Docker / Complex Architectures:** Simplicity and clean code were prioritized over containerizing something that can run natively.



Use of AI Tools



An AI assistant (pair programming) was used to:



* Structure the granular error handling (specific try/except blocks for network, HTTP, and JSON).
* Discuss the difference between INSERT OR REPLACE vs INSERT OR IGNORE and why the latter is better for this feed's idempotency.
* The AI-generated code was manually reviewed and tested.

