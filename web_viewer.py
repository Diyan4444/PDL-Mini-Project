# Project: Combinatorial Counting and Permutation Analyzer
# Group Members (Name - Roll No):
#   Dheer Chheda      - 251080019
#   Diyan Shah        - 251080020
#   Aryan Adivarekar  - 251080008
#   Advait Deodhar    - 251080018
#
# Local web server for the browser version (python web_viewer.py [port]).
# Routes:
#   /                 the page (index.html)
#   /plot/<op>?...    PNG chart for one operation
#   /api/calc?op=...  JSON result for one operation
#   /api/sympy        results of the SymPy checks
# Anything else returns 404, so the source files are never served.

import os
import sys
import json
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

import combinatorics
import recurrence
import visualizer
import sympy_tools

# Localhost only: the server cannot be reached from other machines on the network.
HOST = "127.0.0.1"
DEFAULT_PORT = 8000
# Upper limit for n so a single request cannot tie up the server with a huge computation.
MAX_N = 1000
INDEX_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")


# Raised for invalid user input; the handlers turn it into an HTTP 400 with the message.
class BadRequest(Exception):
    pass


# ---------------------------------------------------------------------------
# Input parsing. params is the dict from urllib.parse.parse_qs: {"n": ["5"], ...}.
# Each parse_* function validates the inputs for one operation and returns keyword
# arguments that match BOTH its calc_* function below and its visualizer.plot_* function.
# ---------------------------------------------------------------------------

def get_text(params, key):
    return params.get(key, [""])[0].strip()


def get_int(params, key, low, high):
    raw = get_text(params, key)
    if not raw:
        raise BadRequest(f"Missing required parameter '{key}'.")
    try:
        value = int(raw)
    except ValueError:
        raise BadRequest(f"Parameter '{key}' must be an integer.")
    if not low <= value <= high:
        raise BadRequest(f"{key} must satisfy {low} <= {key} <= {high}.")
    return value


def get_word(params, max_len):
    word = get_text(params, "word")
    if not word or not word.isalnum():
        raise BadRequest("Word must be alphanumeric.")
    if len(word) > max_len:
        raise BadRequest(f"Word length cannot exceed {max_len} characters.")
    return word


def parse_n(params):
    return {"n": get_int(params, "n", 0, MAX_N)}


def parse_n_r(params):
    n = get_int(params, "n", 0, MAX_N)
    return {"n": n, "r": get_int(params, "r", 0, n)}


def parse_n_r_any(params):
    # For the "with repetition" variants, where r is allowed to be larger than n.
    return {"n": get_int(params, "n", 0, MAX_N), "r": get_int(params, "r", 0, MAX_N)}


def parse_multiset(params):
    return {"text": get_word(params, 50)}


def parse_listing(params):
    mode = get_text(params, "mode")
    if mode in ("multi", "multiset"):
        return {"mode": "multiset", "n": 0, "r": 0, "text": get_word(params, 8)}
    if mode in ("perm", "comb"):
        n = get_int(params, "n", 1, 8)
        return {"mode": mode, "n": n, "r": get_int(params, "r", 1, n), "text": ""}
    raise BadRequest("Invalid listing mode. Expected 'perm', 'comb', or 'multi'.")


def parse_pascal(params):
    return {"num_rows": get_int(params, "rows", 1, 15)}


def parse_recurrence(params):
    # The terms are generated here because the chart needs the sequence itself.
    kind = get_text(params, "type")
    count = get_int(params, "terms", 1, recurrence.MAX_TERMS)
    if kind in ("fib", "fibonacci"):
        return {"rec_type": "fibonacci", "terms": recurrence.fibonacci_sequence(count), "label": "Fibonacci Sequence"}
    if kind in ("fact", "factorial"):
        return {"rec_type": "factorial", "terms": recurrence.factorial_recurrence(count), "label": "Factorial Recurrence"}
    raise BadRequest(f"Unsupported recurrence type '{kind}'.")


def parse_expansion(params):
    return {"n": get_int(params, "n", 0, 20), "a": get_int(params, "a", -10, 10), "b": get_int(params, "b", -10, 10)}


def parse_circular(params):
    # r is optional and defaults to n (all items in the circle). The page sends
    # "allow_reflections"; "reflections" is accepted as a shorter alias.
    n = get_int(params, "n", 0, MAX_N)
    r = get_int(params, "r", 0, n) if get_text(params, "r") else n
    flag = (get_text(params, "allow_reflections") or get_text(params, "reflections")).lower()
    return {"n": n, "r": r, "allow_reflections": flag in ("true", "1", "yes")}


# ---------------------------------------------------------------------------
# Calculations. Each calc_* returns the JSON payload for /api/calc. Big integers are
# sent as strings because JavaScript numbers lose precision above 2^53.
# ---------------------------------------------------------------------------

def calc_factorial(n):
    value = str(combinatorics.factorial(n))
    return {"result": value, "digit_count": len(value)}


def calc_permutations(n, r):
    return {"result": str(combinatorics.permutations(n, r))}


def calc_combinations(n, r):
    return {"result": str(combinatorics.combinations(n, r))}


def calc_comparison(n, r):
    p, c, rf = combinatorics.permutations(n, r), combinatorics.combinations(n, r), combinatorics.factorial(r)
    return {"p": str(p), "c": str(c), "rfact": str(rf), "is_verified": p == c * rf}


def calc_permrep(n, r):
    return {"result": str(combinatorics.permutations_with_repetition(n, r))}


def calc_combrep(n, r):
    return {"result": str(combinatorics.combinations_with_repetition(n, r))}


def calc_multiset(text):
    count, freq = combinatorics.multiset_arrangements_count(text)
    return {"result": str(count), "frequencies": freq, "total_length": len(text)}


def calc_listing(mode, n, r, text):
    if mode == "multiset":
        items, expected, ok = combinatorics.list_multiset_permutations(text)
    else:
        lister = combinatorics.list_letter_permutations if mode == "perm" else combinatorics.list_letter_combinations
        items, expected, ok = lister(n, r)
    return {"items": ["".join(i) for i in items], "count": len(items), "theoretical": expected, "is_match": ok}


def calc_identities(n, r):
    report = combinatorics.verify_binomial_identities(n, r)
    # Convert the big integers to strings but leave the True/False/None flags alone
    # (bool is a subclass of int, hence the extra check).
    return {"report": {k: str(v) if isinstance(v, int) and not isinstance(v, bool) else v for k, v in report.items()}}


def calc_pascal(num_rows):
    return {"triangle": combinatorics.generate_pascal_triangle(num_rows)}


def calc_recurrence(rec_type, terms, label):
    return {"type": rec_type, "label": label, "sequence": [str(t) for t in terms]}


def calc_expansion(n, a, b):
    terms = combinatorics.binomial_expansion_terms(n, a, b)
    return {"formatted": combinatorics.format_binomial_expansion(terms), "terms": [(str(c), xp, yp) for c, xp, yp in terms]}


def calc_derangements(n):
    report = combinatorics.derangements_report(n)
    return {"result": str(report["derangements"]), "factorial": str(report["factorial"]),
            "ratio": report["ratio"], "ratio_approx_1_over_e": report["limit"]}


def calc_circular(n, r, allow_reflections):
    return {"result": str(combinatorics.circular_permutations(n, r, allow_reflections))}


# Every operation the server supports: name -> (parser, calculator, chart function).
# /api/calc and /plot/ both look operations up here, so adding a new operation only
# means writing its parse/calc functions and adding one line.
OPERATIONS = {
    "factorial": (parse_n, calc_factorial, visualizer.plot_factorial),
    "permutations": (parse_n_r, calc_permutations, visualizer.plot_permutations),
    "combinations": (parse_n_r, calc_combinations, visualizer.plot_combinations),
    "comparison": (parse_n_r, calc_comparison, visualizer.plot_comparison),
    "permrep": (parse_n_r_any, calc_permrep, visualizer.plot_perm_with_repetition),
    "combrep": (parse_n_r_any, calc_combrep, visualizer.plot_comb_with_repetition),
    "multiset": (parse_multiset, calc_multiset, visualizer.plot_multiset),
    "listing": (parse_listing, calc_listing, visualizer.plot_listing),
    "identities": (parse_n_r, calc_identities, visualizer.plot_binomial_identities),
    "pascal": (parse_pascal, calc_pascal, visualizer.plot_pascal_triangle),
    "recurrence": (parse_recurrence, calc_recurrence, visualizer.plot_recurrence),
    "expansion": (parse_expansion, calc_expansion, visualizer.plot_binomial_expansion),
    "derangements": (parse_n, calc_derangements, visualizer.plot_derangements),
    "circular": (parse_circular, calc_circular, visualizer.plot_circular_permutations),
}


# ---------------------------------------------------------------------------
# HTTP handling. ThreadingHTTPServer creates one handler object per request.
# ---------------------------------------------------------------------------

class WebViewerHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        # Silence the default one-line log per request to keep the terminal readable.
        pass

    def send(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, code, text):
        self.send(code, text.encode("utf-8"), "text/plain; charset=utf-8")

    def send_json(self, code, data):
        self.send(code, json.dumps(data).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(url.query)
        if url.path in ("/", "/index.html"):
            self.serve_index()
        elif url.path.startswith("/plot/"):
            self.handle_plot(url.path[len("/plot/"):], params)
        elif url.path == "/api/calc":
            self.handle_calc(get_text(params, "op"), params)
        elif url.path == "/api/sympy":
            self.send_json(200, {"success": True, "sympy": sympy_tools.run_all_symbolic_checks()})
        else:
            self.send_text(404, "Not Found")

    def serve_index(self):
        try:
            with open(INDEX_HTML_PATH, "rb") as f:
                self.send(200, f.read(), "text/html; charset=utf-8")
        except OSError:
            self.send_text(500, "index.html file not found on server.")

    def handle_plot(self, op, params):
        if op not in OPERATIONS:
            self.send_text(404, f"Unknown operation '{op}'.")
            return
        if not visualizer.MATPLOTLIB_AVAILABLE:
            self.send_text(500, "Matplotlib is not installed. To enable charts: pip install matplotlib")
            return
        parse, _, plot = OPERATIONS[op]
        try:
            png = plot(**parse(params), as_bytes=True)
        # ValueError / TypeError come from the maths functions rejecting the input,
        # so like BadRequest they are the caller's mistake (400), not a server error (500).
        except (BadRequest, ValueError, TypeError) as e:
            self.send_text(400, str(e))
            return
        except Exception as e:
            sys.stderr.write(f"[Visualizer Error] {op}: {e}\n")
            self.send_text(500, "Visual explanation could not be generated.")
            return
        self.send(200, png, "image/png")

    def handle_calc(self, op, params):
        if not op:
            self.send_json(400, {"success": False, "engine": "python", "error": "Missing 'op' (operation) parameter."})
            return
        if op not in OPERATIONS:
            self.send_json(404, {"success": False, "engine": "python", "error": f"Unknown calculation operation '{op}'."})
            return
        parse, calc, _ = OPERATIONS[op]
        try:
            payload = calc(**parse(params))
        except (BadRequest, ValueError, TypeError) as e:
            self.send_json(400, {"success": False, "engine": "python", "error": str(e)})
            return
        except Exception as e:
            sys.stderr.write(f"[Calc API Error] {op}: {e}\n")
            self.send_json(500, {"success": False, "engine": "python", "error": "Computation error."})
            return
        self.send_json(200, {"success": True, "engine": "python", "operation": op, **payload})


def run_server(port=DEFAULT_PORT):
    try:
        httpd = ThreadingHTTPServer((HOST, port), WebViewerHandler)
    except OSError:
        print(f"\n[Error] Port {port} is already in use. Close the other program or run: python web_viewer.py {port + 1}")
        return
    # Lets Ctrl+C stop the server without waiting for open connections to finish.
    httpd.daemon_threads = True
    print("=" * 70)
    print("COMBINATORIAL COUNTING & PERMUTATION ANALYZER")
    print(f"Open http://{HOST}:{port} in your browser. Press Ctrl+C to stop.")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping HTTP server...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port '{sys.argv[1]}'. Using default {DEFAULT_PORT}.")
    run_server(port)
