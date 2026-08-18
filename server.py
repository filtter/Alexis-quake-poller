import http.server
import sqlite3
import time

DB_NAME = "earthquakes.db"
PORT = 8000

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # Only respond to the root path "/"
        if self.path != '/':
            self.send_error(404, "Not Found")
            return

        # 1. Calculate time 24 hours ago in milliseconds
        # time.time() gives us seconds, we multiply by 1000 to get milliseconds
        now_ms = int(time.time() * 1000)
        yesterday_ms = now_ms - (24 * 60 * 60 * 1000)

        # 2. Query the database
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Find earthquakes from the last 24h, ordered by largest magnitude
        cursor.execute('''
            SELECT id, magnitude, place, time, url 
            FROM earthquakes 
            WHERE time >= ? 
            ORDER BY magnitude DESC 
            LIMIT 20
        ''', (yesterday_ms,))
        
        rows = cursor.fetchall()
        conn.close()

        # 3. Build basic HTML (no pretty designs, pure content)
        html = """
        <html>
        <head><title>Resilient Earthquake Dashboard</title></head>
        <body>
            <h1>Top 20 Earthquakes in the last 24 hours</h1>
            <table border="1" cellpadding="5" style="border-collapse: collapse;">
                <tr>
                    <th>Magnitude</th>
                    <th>Place</th>
                    <th>Time (UTC)</th>
                    <th>Details</th>
                </tr>
        """
        
        if not rows:
            html += "<tr><td colspan='4'>No data yet. Waiting for the poller...</td></tr>"
        
        for row in rows:
            quake_id, mag, place, time_ms, url = row
            
            # Convert milliseconds to readable date format
            # We use time.gmtime to get UTC time and avoid local timezone shifts
            readable_time = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(time_ms / 1000.0))
            
            html += f"""
                <tr>
                    <td>{mag if mag is not None else 'N/A'}</td>
                    <td>{place if place is not None else 'Unknown'}</td>
                    <td>{readable_time}</td>
                    <td><a href="{url if url else '#'}" target="_blank">View details</a></td>
                </tr>
            """
            
        html += """
            </table>
            <p><i>Data provided by USGS. Server running on Python standard library.</i></p>
        </body>
        </html>
        """

        # 4. Send HTTP response
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

def run_server():
    server_address = ('', PORT)
    httpd = http.server.HTTPServer(server_address, DashboardHandler)
    print(f"Dashboard running at http://localhost:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()