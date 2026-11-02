# Project: Combinatorial Counting and Permutation Analyzer
# Name: [YOUR NAME]  Roll No: [YOUR ROLL NO]
# Module: web_viewer.py - Local Python HTTP server serving index.html, calculation APIs, and dynamic visualizations

import os
import sys
import json
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

import combinatorics
import recurrence
import visualizer
import history_manager
import sympy_tools


HOST = "127.0.0.1"
DEFAULT_PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")


class WebViewerHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests for index.html, /api/calc endpoints, and dynamic matplotlib plot generation."""

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

    def send_json_response(self, code, data_dict):
        """Sends a clean JSON response with no caching."""
        body = json.dumps(data_dict).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
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
            if len(parsed.query) > 2000:
                self.send_plain_error(400, "Query string too long (maximum 2000 characters).")
                return

            self.handle_plot_request(path[6:], parsed.query)
            return

        # Route C: Primary calculation API
        if path == "/api/calc" or path.startswith("/api/calc/"):
            op = path[10:] if path.startswith("/api/calc/") else None
            self.handle_api_calc(op, parsed.query)
            return

        # Route D: History API
        if path == "/api/history":
            self.handle_api_history_get(parsed.query)
            return

        # Route E: SymPy API
        if path == "/api/sympy":
            self.handle_api_sympy()
            return

        # All other paths (including /favicon.ico and source files) return 404
        self.send_plain_error(404, "Not Found")

    def do_POST(self):
        # Reject path traversal
        if ".." in self.path or "//" in self.path:
            self.send_plain_error(404, "Not Found")
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        if content_len > 100000:
            self.send_plain_error(400, "Request body too large.")
            return

        body_bytes = self.rfile.read(content_len) if content_len > 0 else b""

        # Route C: Primary calculation API (POST)
        if path == "/api/calc" or path.startswith("/api/calc/"):
            op = path[10:] if path.startswith("/api/calc/") else None
            self.handle_api_calc_post(op, body_bytes, parsed.query)
            return

        # Route D: History API (POST)
        if path == "/api/history":
            self.handle_api_history_post(body_bytes)
            return

        # Route E: SymPy API (POST)
        if path == "/api/sympy":
            self.handle_api_sympy()
            return

        self.send_plain_error(404, "Not Found")

    def do_DELETE(self):
        if ".." in self.path or "//" in self.path:
            self.send_plain_error(404, "Not Found")
            return

        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/history":
            history_manager.clear_history()
            self.send_json_response(200, {"success": True, "message": "History cleared successfully."})
            return

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

    def parse_int_param(self, params, key, min_val, max_val, name_label):
        """Extracts and validates an integer parameter within range."""
        raw_list = params.get(key)
        if not raw_list or not str(raw_list[0]).strip():
            return None, f"Missing required parameter '{key}'."
        raw = str(raw_list[0]).strip()
        try:
            val = int(raw)
        except ValueError:
            return None, f"Parameter '{key}' must be an integer."
        if val < min_val or val > max_val:
            return None, f"{name_label} must satisfy {min_val} <= {key} <= {max_val}."
        return val, None

    # =========================================================================
    # VISUALIZATION /plot/ ENDPOINT
    # =========================================================================

    def handle_plot_request(self, operation, query_string):
        """Validates parameters, invokes visualizer.py, and returns PNG bytes."""
        valid_operations = {
            "factorial", "permutations", "combinations", "comparison",
            "permrep", "combrep", "multiset", "listing",
            "identities", "pascal", "recurrence", "expansion",
            "derangements", "circular"
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
                        return None, "Coefficients and initial values must have absolute value <= 1000 for the visual explanation."
                    coeffs_list.append(c_val)

                inits_list = []
                for ip in init_parts:
                    try:
                        a_val = int(ip)
                    except ValueError:
                        return None, f"Invalid initial value '{ip}'."
                    if abs(a_val) > 1000:
                        return None, "Coefficients and initial values must have absolute value <= 1000 for the visual explanation."
                    inits_list.append(a_val)

                if coeffs_list[-1] == 0:
                    return None, f"Trailing coefficient c{order} cannot be 0."

                seq = recurrence.custom_linear_recurrence(order, coeffs_list, tuple(inits_list), terms)
                with visualizer.PLOT_LOCK:
                    return visualizer.plot_recurrence("custom", seq, label=f"Custom Recurrence (Order {order})", as_bytes=True), None
            else:
                return None, f"Unsupported recurrence type '{rec_type}'."

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

        # 13. Derangements
        elif operation == "derangements":
            n, err = self.parse_int_param(params, "n", 0, 1000, "n")
            if err:
                return None, err
            with visualizer.PLOT_LOCK:
                return visualizer.plot_derangements(n, as_bytes=True), None

        # 14. Circular Permutations
        elif operation == "circular":
            n, err = self.parse_int_param(params, "n", 0, 1000, "n")
            if err:
                return None, err
            raw_r = params.get("r", [""])[0].strip()
            if raw_r:
                r, err = self.parse_int_param(params, "r", 0, n, "r")
                if err:
                    return None, err
            else:
                r = n
            raw_refl = params.get("allow_reflections", [""])[0].strip().lower() or params.get("reflections", [""])[0].strip().lower()
            allow_reflections = (raw_refl in ("true", "1", "yes"))
            with visualizer.PLOT_LOCK:
                return visualizer.plot_circular_permutations(n, r=r, allow_reflections=allow_reflections, as_bytes=True), None

        else:
            return None, f"Unknown operation '{operation}'."

    # =========================================================================
    # PRIMARY PYTHON CALCULATION API (/api/calc)
    # =========================================================================

    def extract_calc_params(self, raw_op, query_string, body_bytes=b""):
        """Extracts operation name and parameter dictionary from query string or JSON/form body."""
        params = {}
        if query_string:
            parsed = urllib.parse.parse_qs(query_string)
            for k, v in parsed.items():
                params[k] = v[0] if len(v) == 1 else v

        if body_bytes:
            content_type = self.headers.get("Content-Type", "")
            if "application/json" in content_type:
                try:
                    json_data = json.loads(body_bytes.decode("utf-8"))
                    if isinstance(json_data, dict):
                        params.update(json_data)
                except Exception:
                    pass
            else:
                try:
                    form_parsed = urllib.parse.parse_qs(body_bytes.decode("utf-8"))
                    for k, v in form_parsed.items():
                        params[k] = v[0] if len(v) == 1 else v
                except Exception:
                    pass

        op = raw_op or params.get("op") or params.get("operation")
        # Normalize params format so parse_int_param can read single values or lists
        normalized = {}
        for k, v in params.items():
            if isinstance(v, list):
                normalized[k] = [str(x) for x in v]
            else:
                normalized[k] = [str(v)]
        return op, normalized

    def handle_api_calc(self, op, query_string):
        """Processes GET calculation request and responds with structured JSON."""
        resolved_op, params = self.extract_calc_params(op, query_string)
        self.execute_and_respond_calc(resolved_op, params)

    def handle_api_calc_post(self, op, body_bytes, query_string):
        """Processes POST calculation request and responds with structured JSON."""
        resolved_op, params = self.extract_calc_params(op, query_string, body_bytes)
        self.execute_and_respond_calc(resolved_op, params)

    def execute_and_respond_calc(self, op, params):
        """Validates parameters, executes pure Python math functions, and returns JSON."""
        if not op:
            self.send_json_response(400, {
                "success": False,
                "engine": "python",
                "error": "Missing 'op' (operation) parameter."
            })
            return

        valid_calc_ops = {
            "factorial", "permutations", "combinations", "comparison",
            "permrep", "combrep", "multiset", "listing",
            "identities", "pascal", "recurrence", "expansion",
            "derangements", "circular"
        }
        if op not in valid_calc_ops:
            self.send_json_response(404, {
                "success": False,
                "engine": "python",
                "error": f"Unknown calculation operation '{op}'."
            })
            return

        try:
            # 1. Factorial
            if op == "factorial":
                n, err = self.parse_int_param(params, "n", 0, 1000, "n")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                res = combinatorics.factorial(n)
                res_str = str(res)
                history_manager.save_history_record("Factorial", f"n={n}", res_str)
                self.send_json_response(200, {
                    "success": True,
                    "engine": "python",
                    "operation": "factorial",
                    "n": n,
                    "result": res_str,
                    "digit_count": len(res_str),
                    "explanation": f"Product of all positive integers from 1 up to {n}."
                })
                return

            # 2. Permutations
            elif op == "permutations":
                n, err = self.parse_int_param(params, "n", 0, 1000, "n")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                r, err = self.parse_int_param(params, "r", 0, n, "r")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                res = combinatorics.permutations(n, r)
                res_str = str(res)
                history_manager.save_history_record("Permutations", f"n={n}, r={r}", res_str)
                self.send_json_response(200, {
                    "success": True,
                    "engine": "python",
                    "operation": "permutations",
                    "n": n,
                    "r": r,
                    "result": res_str,
                    "digit_count": len(res_str),
                    "explanation": f"P({n}, {r}) = {n}! / ({n} - {r})! = {res_str}"
                })
                return

            # 3. Combinations
            elif op == "combinations":
                n, err = self.parse_int_param(params, "n", 0, 1000, "n")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                r, err = self.parse_int_param(params, "r", 0, n, "r")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                res = combinatorics.combinations(n, r)
                res_str = str(res)
                history_manager.save_history_record("Combinations", f"n={n}, r={r}", res_str)
                self.send_json_response(200, {
                    "success": True,
                    "engine": "python",
                    "operation": "combinations",
                    "n": n,
                    "r": r,
                    "result": res_str,
                    "digit_count": len(res_str),
                    "explanation": f"C({n}, {r}) = {n}! / ({r}! * ({n} - {r})!) = {res_str}"
                })
                return

            # 4. Comparison
            elif op == "comparison":
                n, err = self.parse_int_param(params, "n", 0, 1000, "n")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                r, err = self.parse_int_param(params, "r", 0, n, "r")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                p = combinatorics.permutations(n, r)
                c = combinatorics.combinations(n, r)
                rf = combinatorics.factorial(r)
                prod = c * rf
                is_verified = (p == prod)
                history_manager.save_history_record("Comparison", f"n={n}, r={r}", f"P={p}, C={c}, r!={rf}")
                self.send_json_response(200, {
                    "success": True,
                    "engine": "python",
                    "operation": "comparison",
                    "n": n,
                    "r": r,
                    "p": str(p),
                    "c": str(c),
                    "rfact": str(rf),
                    "is_verified": is_verified,
                    "explanation": f"P({n}, {r}) = C({n}, {r}) * {r}! = {str(prod)}"
                })
                return

            # 5. Permutations with Repetition
            elif op == "permrep":
                n, err = self.parse_int_param(params, "n", 0, 1000, "n")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                r, err = self.parse_int_param(params, "r", 0, 1000, "r")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                res = combinatorics.permutations_with_repetition(n, r)
                res_str = str(res)
                history_manager.save_history_record("Permutations with Repetition", f"n={n}, r={r}", res_str)
                self.send_json_response(200, {
                    "success": True,
                    "engine": "python",
                    "operation": "permrep",
                    "n": n,
                    "r": r,
                    "result": res_str,
                    "explanation": f"{n}^{r} = {res_str}"
                })
                return

            # 6. Combinations with Repetition
            elif op == "combrep":
                n, err = self.parse_int_param(params, "n", 0, 1000, "n")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                r, err = self.parse_int_param(params, "r", 0, 1000, "r")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                res = combinatorics.combinations_with_repetition(n, r)
                res_str = str(res)
                history_manager.save_history_record("Combinations with Repetition", f"n={n}, r={r}", res_str)
                self.send_json_response(200, {
                    "success": True,
                    "engine": "python",
                    "operation": "combrep",
                    "n": n,
                    "r": r,
                    "result": res_str,
                    "explanation": f"C({n} + {r} - 1, {r}) = {res_str}"
                })
                return

            # 7. Multiset
            elif op == "multiset":
                raw_word = params.get("word", [""])[0].strip()
                if not raw_word or not raw_word.isalnum():
                    self.send_json_response(400, {"success": False, "engine": "python", "error": "Word must be alphanumeric."})
                    return
                count, freq = combinatorics.multiset_arrangements_count(raw_word)
                res_str = str(count)
                history_manager.save_history_record("Multiset Arrangements", f"word='{raw_word}'", res_str)
                self.send_json_response(200, {
                    "success": True,
                    "engine": "python",
                    "operation": "multiset",
                    "word": raw_word,
                    "frequencies": freq,
                    "total_length": len(raw_word),
                    "result": res_str
                })
                return

            # 8. Listing
            elif op == "listing":
                raw_mode = params.get("mode", [""])[0].strip()
                if raw_mode in ("multi", "multiset"):
                    word = params.get("word", [""])[0].strip()
                    if not word or not word.isalnum() or len(word) > 8:
                        self.send_json_response(400, {"success": False, "engine": "python", "error": "Word must be alphanumeric (max 8 characters)."})
                        return
                    items, theo, is_match = combinatorics.list_multiset_permutations(word)
                    display_items = ["".join(tup) for tup in items]
                else:
                    n, err = self.parse_int_param(params, "n", 1, 8, "n")
                    if err:
                        self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                        return
                    r, err = self.parse_int_param(params, "r", 1, n, "r")
                    if err:
                        self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                        return
                    if raw_mode == "perm":
                        items, theo, is_match = combinatorics.list_letter_permutations(n, r)
                    else:
                        items, theo, is_match = combinatorics.list_letter_combinations(n, r)
                    display_items = ["".join(tup) for tup in items]

                self.send_json_response(200, {
                    "success": True,
                    "engine": "python",
                    "operation": "listing",
                    "items": display_items,
                    "count": len(display_items),
                    "theoretical": theo,
                    "is_match": is_match
                })
                return

            # 9. Identities
            elif op == "identities":
                n, err = self.parse_int_param(params, "n", 0, 1000, "n")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                r, err = self.parse_int_param(params, "r", 0, n, "r")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                rep = combinatorics.verify_binomial_identities(n, r)
                # Convert large ints to strings for JSON safety
                safe_rep = {
                    "n": rep["n"],
                    "r": rep["r"],
                    "c_nr": str(rep["c_nr"]),
                    "symmetry_verified": rep["symmetry_verified"],
                    "c_sym": str(rep["c_sym"]),
                    "pascal_applicable": rep["pascal_applicable"],
                    "pascal_verified": rep["pascal_verified"],
                    "pascal_note": rep["pascal_note"],
                    "row_sum_verified": rep["row_sum_verified"],
                    "row_sum_value": str(rep["row_sum_value"]),
                    "power_of_two": str(rep["power_of_two"])
                }
                history_manager.save_history_record("Binomial Identities", f"n={n}, r={r}", f"Symmetry={rep['symmetry_verified']}, RowSum={rep['row_sum_verified']}")
                self.send_json_response(200, {
                    "success": True,
                    "engine": "python",
                    "operation": "identities",
                    "report": safe_rep
                })
                return

            # 10. Pascal
            elif op == "pascal":
                rows, err = self.parse_int_param(params, "rows", 1, 15, "rows")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                tri = combinatorics.generate_pascal_triangle(rows)
                history_manager.save_history_record("Pascal's Triangle", f"rows={rows}", f"Generated {rows} rows")
                self.send_json_response(200, {
                    "success": True,
                    "engine": "python",
                    "operation": "pascal",
                    "rows": rows,
                    "triangle": tri
                })
                return

            # 11. Recurrence
            elif op == "recurrence":
                rec_type = params.get("type", [""])[0].strip()
                terms, err = self.parse_int_param(params, "terms", 1, 50, "terms")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return

                if rec_type in ("fib", "fibonacci"):
                    seq = recurrence.fibonacci_sequence(terms)
                    label = "Fibonacci Sequence"
                elif rec_type in ("fact", "factorial"):
                    seq = recurrence.factorial_recurrence(terms)
                    label = "Factorial Recurrence"
                elif rec_type == "custom":
                    order, err = self.parse_int_param(params, "order", 1, 5, "order")
                    if err:
                        self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                        return

                    raw_coeffs = params.get("coeffs", [""])[0].strip()
                    raw_inits = params.get("inits", [""])[0].strip()
                    coeff_parts = [c.strip() for c in raw_coeffs.split(",") if c.strip()]
                    init_parts = [a.strip() for a in raw_inits.split(",") if a.strip()]

                    if len(coeff_parts) != order or len(init_parts) != order:
                        self.send_json_response(400, {"success": False, "engine": "python", "error": f"Expected {order} coefficients and {order} initial values."})
                        return

                    coeffs_list = [int(c) for c in coeff_parts]
                    inits_list = [int(a) for a in init_parts]
                    if coeffs_list[-1] == 0:
                        self.send_json_response(400, {"success": False, "engine": "python", "error": f"Trailing coefficient c{order} cannot be 0."})
                        return

                    seq = recurrence.custom_linear_recurrence(order, coeffs_list, tuple(inits_list), terms)
                    label = f"Custom Recurrence (Order {order})"
                else:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": f"Unsupported recurrence type '{rec_type}'."})
                    return

                history_manager.save_history_record("Recurrence Relations", f"type={rec_type}, terms={terms}", f"{len(seq)} terms")
                self.send_json_response(200, {
                    "success": True,
                    "engine": "python",
                    "operation": "recurrence",
                    "type": rec_type,
                    "terms": terms,
                    "sequence": [str(x) for x in seq],
                    "label": label
                })
                return

            # 12. Expansion
            elif op == "expansion":
                n, err = self.parse_int_param(params, "n", 0, 20, "n")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                a, err = self.parse_int_param(params, "a", -10, 10, "a")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                b, err = self.parse_int_param(params, "b", -10, 10, "b")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                terms = combinatorics.binomial_expansion_terms(n, a, b)
                formatted = combinatorics.format_binomial_expansion(terms)
                history_manager.save_history_record("Binomial Expansion", f"n={n}, a={a}, b={b}", formatted)
                self.send_json_response(200, {
                    "success": True,
                    "engine": "python",
                    "operation": "expansion",
                    "n": n,
                    "a": a,
                    "b": b,
                    "formatted": formatted,
                    "terms": [(str(c), xp, yp) for c, xp, yp in terms]
                })
                return

            # 13. Derangements
            elif op == "derangements":
                n, err = self.parse_int_param(params, "n", 0, 1000, "n")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                rep = combinatorics.derangements_report(n)
                res_str = str(rep["derangements"])
                history_manager.save_history_record("Derangements", f"n={n}", res_str)
                self.send_json_response(200, {
                    "success": True,
                    "engine": "python",
                    "operation": "derangements",
                    "n": n,
                    "result": res_str,
                    "factorial": str(rep["factorial"]),
                    "ratio": rep["ratio"],
                    "ratio_approx_1_over_e": rep["ratio_approx_1_over_e"],
                    "recurrence_formula": rep["recurrence_formula"],
                    "inclusion_exclusion_formula": rep["inclusion_exclusion_formula"]
                })
                return

            # 14. Circular Permutations
            elif op == "circular":
                n, err = self.parse_int_param(params, "n", 0, 1000, "n")
                if err:
                    self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                    return
                raw_r = params.get("r", [""])[0].strip()
                if raw_r:
                    r, err = self.parse_int_param(params, "r", 0, n, "r")
                    if err:
                        self.send_json_response(400, {"success": False, "engine": "python", "error": err})
                        return
                else:
                    r = None

                raw_refl = params.get("allow_reflections", [""])[0].strip().lower() or params.get("reflections", [""])[0].strip().lower()
                allow_reflections = (raw_refl in ("true", "1", "yes"))

                rep = combinatorics.circular_permutations_report(n, r=r, allow_reflections=allow_reflections)
                res_str = str(rep["count"])
                history_manager.save_history_record("Circular Permutations", f"n={n}, r={r}, refl={allow_reflections}", res_str)
                self.send_json_response(200, {
                    "success": True,
                    "engine": "python",
                    "operation": "circular",
                    "n": n,
                    "r": rep["r"],
                    "result": res_str,
                    "allow_reflections": rep["allow_reflections"],
                    "explanation": rep["explanation"]
                })
                return

        except Exception as e:
            sys.stderr.write(f"[Calc API Error] {e}\n")
            self.send_json_response(500, {"success": False, "engine": "python", "error": f"Computation error: {str(e)}"})

    # =========================================================================
    # HISTORY API (/api/history)
    # =========================================================================

    def handle_api_history_get(self, query_string):
        """Returns history records from history.txt as JSON."""
        params = urllib.parse.parse_qs(query_string)
        q = params.get("q", [""])[0].strip()
        if q:
            records, total, skipped = history_manager.search_history_records(q)
        else:
            records, skipped = history_manager.read_history_records()
            total = len(records)

        self.send_json_response(200, {
            "success": True,
            "records": records,
            "history": records,
            "total": total,
            "skipped": skipped
        })

    def handle_api_history_post(self, body_bytes):
        """Appends a new history record to history.txt."""
        try:
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            self.send_json_response(400, {"success": False, "error": "Invalid JSON."})
            return

        op = data.get("operation", "Custom Calculation")
        inputs_str = data.get("inputs", "") or data.get("parameters", "")
        res_str = data.get("result", "")

        ok = history_manager.save_history_record(op, inputs_str, res_str)
        self.send_json_response(200, {"success": ok})

    # =========================================================================
    # SYMPY API (/api/sympy)
    # =========================================================================

    def handle_api_sympy(self):
        """Executes SymPy formal symbolic verification checks and returns JSON."""
        result = sympy_tools.run_all_symbolic_checks()
        self.send_json_response(200, {
            "success": True,
            "sympy": result
        })


def run_server(port=DEFAULT_PORT):
    """Starts the ThreadingHTTPServer on 127.0.0.1:port."""
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
