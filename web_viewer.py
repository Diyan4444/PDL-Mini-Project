# Project: Combinatorial Counting and Permutation Analyzer
# Name: [YOUR NAME]  Roll No: [YOUR ROLL NO]
# Module: web_viewer.py - Local Python HTTP server serving index.html and dynamic matplotlib visualizations

import os
import sys
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

import combinatorics
import recurrence
import visualizer


HOST = "127.0.0.1"
DEFAULT_PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")


class WebViewerHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests for index.html and dynamic matplotlib plot generation."""

    def log_message(self, format_str, *args):
        """Silences standard request logs for cleaner console output."""
        return

    def send_plain_error(self, code, message):
        """Sends a clean plain-text error response with no internal tracebacks."""
        body = message.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Reject path traversal attempts immediately
        if ".." in self.path or "//" in self.path:
            self.send_plain_error(404, "Not Found")
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Route A: Serve main application interface (index.html)
        if path in ("/", "/index.html"):
            self.serve_index_html()
            return

        # Route B: Dynamic image generation endpoints
        if path.startswith("/plot/"):
            # Reject excessively long query strings (safety check)
            if len(parsed.query) > 2000:
                self.send_plain_error(400, "Query string too long (maximum 2000 characters).")
                return

            self.handle_plot_request(path[6:], parsed.query)
            return

        # All other paths (including /favicon.ico and source files) return 404
        self.send_plain_error(404, "Not Found")

    def serve_index_html(self):
        """Reads and serves the project's index.html file."""
        if not os.path.exists(INDEX_HTML_PATH):
            self.send_plain_error(500, "index.html file not found on server.")
            return

        try:
            with open(INDEX_HTML_PATH, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            sys.stderr.write(f"[Server Error] Failed to read index.html: {e}\n")
            self.send_plain_error(500, "Internal Server Error")

    def handle_plot_request(self, operation, query_string):
        """Validates parameters, invokes visualizer.py, and returns PNG bytes."""
        valid_operations = {
            "factorial", "permutations", "combinations", "comparison",
            "permrep", "combrep", "multiset", "listing",
            "identities", "pascal", "recurrence", "expansion"
        }
        if operation not in valid_operations:
            self.send_plain_error(404, f"Unknown operation '{operation}'.")
            return

        if not visualizer.is_matplotlib_available():
            self.send_plain_error(500, "Matplotlib is not installed. To enable charts: pip install matplotlib")
            return

        params = urllib.parse.parse_qs(query_string)

        try:
            png_bytes, err_msg = self.generate_plot_bytes(operation, params)
        except Exception as e:
            sys.stderr.write(f"[Visualizer Error] Exception generating plot for '{operation}': {e}\n")
            self.send_plain_error(500, "Visual explanation could not be generated.")
            return

        if err_msg is not None:
            self.send_plain_error(400, err_msg)
            return

        if not png_bytes or not isinstance(png_bytes, bytes):
            self.send_plain_error(500, "Visual explanation could not be generated.")
            return

        # Return successful PNG image
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(png_bytes)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(png_bytes)

    def parse_int_param(self, params, key, min_val, max_val, name_label):
        """Extracts and validates an integer parameter within range."""
        raw_list = params.get(key)
        if not raw_list or not raw_list[0].strip():
            return None, f"Missing required parameter '{key}'."
        raw = raw_list[0].strip()
        try:
            val = int(raw)
        except ValueError:
            return None, f"Parameter '{key}' must be an integer."
        if val < min_val or val > max_val:
            return None, f"{name_label} must satisfy {min_val} <= {key} <= {max_val}."
        return val, None

    def generate_plot_bytes(self, operation, params):
        """Validates inputs per operation and invokes visualizer with thread safety."""
        # 1. Factorial
        if operation == "factorial":
            n, err = self.parse_int_param(params, "n", 0, 1000, "n")
            if err:
                return None, err
            with visualizer.PLOT_LOCK:
                return visualizer.plot_factorial(n, as_bytes=True), None

        # 2. Permutations
        elif operation == "permutations":
            n, err = self.parse_int_param(params, "n", 0, 1000, "n")
            if err:
                return None, err
            r, err = self.parse_int_param(params, "r", 0, n, "r")
            if err:
                return None, err
            with visualizer.PLOT_LOCK:
                return visualizer.plot_permutations(n, r, as_bytes=True), None

        # 3. Combinations
        elif operation == "combinations":
            n, err = self.parse_int_param(params, "n", 0, 1000, "n")
            if err:
                return None, err
            r, err = self.parse_int_param(params, "r", 0, n, "r")
            if err:
                return None, err
            with visualizer.PLOT_LOCK:
                return visualizer.plot_combinations(n, r, as_bytes=True), None

        # 4. Comparison
        elif operation == "comparison":
            n, err = self.parse_int_param(params, "n", 0, 1000, "n")
            if err:
                return None, err
            r, err = self.parse_int_param(params, "r", 0, n, "r")
            if err:
                return None, err
            with visualizer.PLOT_LOCK:
                return visualizer.plot_comparison(n, r, as_bytes=True), None

        # 5. Permutations with Repetition
        elif operation == "permrep":
            n, err = self.parse_int_param(params, "n", 0, 1000, "n")
            if err:
                return None, err
            r, err = self.parse_int_param(params, "r", 0, 1000, "r")
            if err:
                return None, err
            with visualizer.PLOT_LOCK:
                return visualizer.plot_perm_with_repetition(n, r, as_bytes=True), None

        # 6. Combinations with Repetition
        elif operation == "combrep":
            n, err = self.parse_int_param(params, "n", 0, 1000, "n")
            if err:
                return None, err
            r, err = self.parse_int_param(params, "r", 0, 1000, "r")
            if err:
                return None, err
            with visualizer.PLOT_LOCK:
                return visualizer.plot_comb_with_repetition(n, r, as_bytes=True), None

        # 7. Multiset
        elif operation == "multiset":
            raw_word = params.get("word", [""])[0].strip()
            if not raw_word:
                return None, "Word parameter is required."
            if len(raw_word) > 50:
                return None, "Word length cannot exceed 50 characters."
            if not raw_word.isalnum():
                return None, "Word must be alphanumeric."
            with visualizer.PLOT_LOCK:
                return visualizer.plot_multiset(raw_word, as_bytes=True), None

        # 8. Listing
        elif operation == "listing":
            raw_mode = params.get("mode", [""])[0].strip()
            if raw_mode not in ("perm", "comb", "multi", "multiset"):
                return None, "Invalid listing mode. Expected 'perm', 'comb', or 'multi'."

            if raw_mode in ("multi", "multiset"):
                word = params.get("word", [""])[0].strip()
                if not word:
                    return None, "Word parameter is required for multiset listing."
                if len(word) > 8:
                    return None, "Word length cannot exceed 8 characters for listing."
                if not word.isalnum():
                    return None, "Word must be alphanumeric."
                with visualizer.PLOT_LOCK:
                    return visualizer.plot_listing("multiset", 0, 0, word, as_bytes=True), None
            else:
                n, err = self.parse_int_param(params, "n", 1, 8, "n")
                if err:
                    return None, err
                r, err = self.parse_int_param(params, "r", 1, n, "r")
                if err:
                    return None, err
                target_mode = "perm" if raw_mode == "perm" else "comb"
                with visualizer.PLOT_LOCK:
                    return visualizer.plot_listing(target_mode, n, r, "", as_bytes=True), None

        # 9. Binomial Identities
        elif operation == "identities":
            n, err = self.parse_int_param(params, "n", 0, 1000, "n")
            if err:
                return None, err
            r, err = self.parse_int_param(params, "r", 0, n, "r")
            if err:
                return None, err
            with visualizer.PLOT_LOCK:
                return visualizer.plot_binomial_identities(n, r, as_bytes=True), None

        # 10. Pascal Triangle
        elif operation == "pascal":
            rows, err = self.parse_int_param(params, "rows", 1, 15, "rows")
            if err:
                return None, err
            with visualizer.PLOT_LOCK:
                return visualizer.plot_pascal_triangle(rows, as_bytes=True), None

        # 11. Recurrence
        elif operation == "recurrence":
            rec_type = params.get("type", [""])[0].strip()
            terms, err = self.parse_int_param(params, "terms", 1, 50, "terms")
            if err:
                return None, err

            if rec_type in ("fib", "fibonacci"):
                seq = recurrence.fibonacci_sequence(terms)
                with visualizer.PLOT_LOCK:
                    return visualizer.plot_recurrence("fibonacci", seq, label="Fibonacci Sequence", as_bytes=True), None
            elif rec_type in ("fact", "factorial"):
                seq = recurrence.factorial_recurrence(terms)
                with visualizer.PLOT_LOCK:
                    return visualizer.plot_recurrence("factorial", seq, label="Factorial Recurrence", as_bytes=True), None
            elif rec_type == "custom":
                order, err = self.parse_int_param(params, "order", 1, 5, "order")
                if err:
                    return None, err

                raw_coeffs = params.get("coeffs", [""])[0].strip()
                raw_inits = params.get("inits", [""])[0].strip()
                if not raw_coeffs or not raw_inits:
                    return None, "Custom recurrence requires 'coeffs' and 'inits' parameters."

                coeff_parts = [c.strip() for c in raw_coeffs.split(",") if c.strip()]
                init_parts = [a.strip() for a in raw_inits.split(",") if a.strip()]

                if len(coeff_parts) != order:
                    return None, f"Expected {order} coefficients for order {order}, got {len(coeff_parts)}."
                if len(init_parts) != order:
                    return None, f"Expected {order} initial values for order {order}, got {len(init_parts)}."

                coeffs_list = []
                for cp in coeff_parts:
                    try:
                        c_val = int(cp)
                    except ValueError:
                        return None, f"Invalid coefficient value '{cp}'."
                    if abs(c_val) > 1000:
                        return None, "Coefficients and initial values must have absolute value <= 1000 for the visual"
                    coeffs_list.append(c_val)

                inits_list = []
                for ip in init_parts:
                    try:
                        a_val = int(ip)
                    except ValueError:
                        return None, f"Invalid initial value '{ip}'."
                    if abs(a_val) > 1000:
                        return None, "Coefficients and initial values must have absolute value <= 1000 for the visual"
                    inits_list.append(a_val)

                if coeffs_list[-1] == 0:
                    return None, f"Trailing coefficient c{order} cannot be 0."

                seq = recurrence.custom_linear_recurrence(order, coeffs_list, tuple(inits_list), terms)
                with visualizer.PLOT_LOCK:
                    return visualizer.plot_recurrence("custom", seq, label=f"Custom Order {order}", as_bytes=True), None
            else:
                return None, "Invalid recurrence type. Expected 'fib', 'fact', or 'custom'."

        # 12. Binomial Expansion
        elif operation == "expansion":
            n, err = self.parse_int_param(params, "n", 0, 20, "n")
            if err:
                return None, err
            a, err = self.parse_int_param(params, "a", -10, 10, "a")
            if err:
                return None, err
            b, err = self.parse_int_param(params, "b", -10, 10, "b")
            if err:
                return None, err
            with visualizer.PLOT_LOCK:
                return visualizer.plot_binomial_expansion(n, a, b, as_bytes=True), None

        else:
            return None, f"Unknown operation '{operation}'."


def run_server(port=DEFAULT_PORT):
    """Starts the ThreadingHTTPServer on 127.0.0.1:port."""
    # Pre-import matplotlib to warm up backend on server startup
    if visualizer.is_matplotlib_available():
        try:
            import matplotlib.pyplot
        except Exception:
            pass

    server_address = (HOST, port)
    try:
        httpd = ThreadingHTTPServer(server_address, WebViewerHandler)
        httpd.daemon_threads = True
    except OSError as e:
        print(f"\n[Error] Port {port} is already in use. Close the other program or run: python web_viewer.py {port + 1}")
        return

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
        print("Server shutdown cleanly.")


if __name__ == "__main__":
    port_to_use = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port_to_use = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port '{sys.argv[1]}'. Using default {DEFAULT_PORT}.")
    run_server(port_to_use)
