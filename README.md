# Webserver for stock market analysis made with Flask:

- All Time High: An all-time high for a given date refers to the date when a symbol achieved a breakthrough in its high value within the OHLCV matrix.

- Chart Patterns: Head-&-Shoulders (HS), Inverse HS, Double Top and Double Bottom 

---

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Install and Run

1. Install the package:
   ```bash
   pip install fintech-webserver
   ```

3. Start the server:
   ```bash
   fintech run
   ```

---


Use `fintech --help` to read the man page of `fintech` command.

Optionally, create a file named `.flaskenv` in current working directory to specify common options as below:
```
PROFILE=Development
FLASK_RUN_DEBUG=True
FLASK_RUN_PORT=8090
FLASK_RUN_HOST=0.0.0.0
```