# 🎲 Combinatorial Counting & Permutation Analyzer

A comprehensive, mathematically rigorous, and visual discrete mathematics exploration tool designed for college students, examiners, and peer reviewers. It computes and visualizes **Permutations, Combinations, Repetition Variants, Multisets, Binomial Identities, Pascal's Triangle, Recurrence Relations, Binomial Expansions, Derangements (Subfactorials), and Circular Permutations**. Powered by pure Python arbitrary-precision arithmetic, every operation dynamically renders a Matplotlib visual explanation chart directly under the result to demonstrate *why* the mathematical formulas work.

---

## ⚡ Three Ways to Use It

- **Web App with Live Engine & Charts (Recommended):** Run `python web_viewer.py` → open http://127.0.0.1:8000
- **Interactive Terminal CLI:** Run `python main.py` (menu options 0 to 18)
- **Direct Browser File:** Double-click `index.html` (runs full calculations offline via client-side BigInt engine; charts gracefully instruct to start the Python server)

---

## 💡 What is This Project About?

Have you ever wondered:
- *In how many ways can 5 runners finish in 1st, 2nd, and 3rd place?* → **Permutations P(n, r)**
- *How many different 3-person project teams can you pick from 10 classmates?* → **Combinations C(n, r)**
- *Why does order matter for passcodes, but not for lottery numbers?* → **P vs C Comparison**
- *How many unique words can you make by rearranging "MISSISSIPPI"?* → **Multisets & Multinomials**
- *In how many secret-Santa drawings does NO ONE receive their own gift?* → **Derangements D(n)**
- *How many unique arrangements exist when seating people or beading reversible necklaces?* → **Circular Permutations**
- *What pattern connects Pascal's triangle to algebraic expansion?* → **Binomial Theorem**

This project answers these questions using exact Python integer arithmetic (zero decimal rounding error) and pairs every calculation with an educational visual explanation.

---

## 🔍 Why Not Just Google the Answer?

Search engines and simple calculators only output a final number without revealing the underlying mathematical structure. This tool shows step-by-step substitutions, algebraic identities, asymptotic limits (such as D(n)/n! → 1/e), and generates synchronized plots illustrating slot choices, subset collapses, stars-and-bars partitions, and rotational symmetry orbits.

---

## 📦 Installation & Setup

**Prerequisite:** Python 3.8+ (`python --version` or `python3` / `py`).

### Step 1: Clone the Repository
```bash
git clone https://github.com/Diyan4444/PDL-Mini-Project.git
cd PDL-Mini-Project
```

### Step 2: Create a Virtual Environment (Recommended)
- **Windows:**
  ```bash
  python -m venv venv
  venv\Scripts\activate
  ```
- **macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```
- `matplotlib`: Generates all 14 dynamic visual explanation charts.
- `sympy`: Optional dependency for formal symbolic verification and recurrence closed-form solvers (`rsolve`).
- *Core mathematical engines, HTTP server, and history management use only the Python standard library.*

---

## 🌐 Starting the Web Server

Start the local Python HTTP server:
```bash
python web_viewer.py
```
The terminal will display:
```
======================================================================
COMBINATORIAL COUNTING & PERMUTATION ANALYZER
Open http://127.0.0.1:8000 in your browser. Press Ctrl+C to stop.
======================================================================
```
1. Open **http://127.0.0.1:8000** in Google Chrome or any browser.
2. The UI connects directly to Python's `/api/calc` backend, badged with `[Python Engine]`.
3. Try entering `5` in **Derangements** — you get exact `D(5) = 44`, ratio `44/120 = 0.3667`, comparison to limit `1/e ≈ 0.3679`, and an inclusion-exclusion partition chart!
4. **Port in use:** Run `python web_viewer.py 8001` and navigate to http://127.0.0.1:8001.

> **Security Note:** The server binds strictly to `127.0.0.1` (localhost only) and whitelists accessible paths to prevent directory traversal and public network exposure.

---

## 💻 Terminal CLI (python main.py)

Run the interactive terminal interface:
```bash
python main.py
```
- Clean numeric menu with options 1 to 18 (`0` to exit).
- Prompts after each calculation to generate and view visual explanation charts.
- **Option 18 (Visual Gallery):** Batch-generates all 14 demonstration charts into the `plots/` folder.
- Non-visual tools (SymPy verification, history search/clear, automated self-tests) run in clean text mode.

---

## 🧪 Run the Automated Tests

Execute the comprehensive automated test suite:
```bash
python tests.py
```
**Test Result:** All **28/28 tests passed** (0 failed).  
The suite validates known mathematical answers, boundary conditions (n=0, 0!=1), boolean type safety rejection, large integer expansion scaling, multiset partitions, recurrence sequences, history persistence, SymPy integration, REST endpoints (`/api/calc`, `/api/history`, `/api/sympy`), security whitelists, and all 14 visualizer chart routines.

---

## 📊 Key Features & Mathematics Table

| # | Feature | Mathematical Formula | Visual Explanation |
|---|---|---|---|
| **1** | Factorial n! | n! = n × (n - 1) × ... × 1 (0! = 1) | Log10 growth curve and multiplication chain |
| **2** | Permutations P(n, r) | P(n, r) = n! / (n - r)! | Shrinking choice slots and distribution curve |
| **3** | Combinations C(n, r) | C(n, r) = n! / (r! × (n - r)!) | Symmetric bell curve and r! subset arrangement collapse |
| **4** | P vs C Comparison | P(n, r) = C(n, r) × r! | Grouped bar chart contrasting ordered vs unordered counts |
| **5** | Permutations w/ Repetition | n^r | Constant choice slots vs shrinking permutation slots |
| **6** | Combinations w/ Repetition | C(n + r - 1, r) | Stars-and-bars divider model with item buckets |
| **7** | Multiset Arrangements | n! / (k1! × k2! × ... × km!) | Letter frequency histogram and duplicate factorial divisions |
| **8** | Listing & Uniqueness | Exhaustive tuple enumeration | Arrangement badge grid with uniqueness verification |
| **9** | Binomial Identities | Symmetry, Pascal rule, Sum = 2^n | Three panels: symmetry, Pascal addition, and row sums |
| **10** | Pascal's Triangle | C(n, k) = C(n-1, k-1) + C(n-1, k) | Centered number pyramid with odd/even parity colouring |
| **11** | Recurrence Analyzer | a(n) = c1*a(n-1) + ... + ck*a(n-k) | Step progression and Golden Ratio (phi ≈ 1.618) convergence |
| **12** | Binomial Expansion | (a*x + b*y)^n via Sum C(n, k) | Signed polynomial coefficients and Pascal row mapping |
| **13** | Derangements D(n) | D(n) = (n - 1) * [D(n-1) + D(n-2)] | Recurrence step bars, ratio D(n)/n!, and 1/e asymptote line |
| **14** | Circular Permutations | P(n, r) / r (Necklaces: ÷ 2) | Rotational circle perimeter layout and symmetry orbits |
| **15** | SymPy Verification | Formal algebraic cross-check & rsolve | Interactive verification cards with live symbolics |
| **16** | Calculation History | Persistent log in history.txt | Audit table with keyword search and clear options |
| **17** | Automated Self-Test | Regression suite covering all modules | Live browser runner with pass/fail badges |
| **18** | Visual Gallery | Batch chart generation (14 plots) | Generates all 14 explanation charts into plots/ |

---

## 🧩 Architectural Design & API Flow

```
Web Browser (index.html)
   │
   ├── [Primary Engine] ──> GET /api/calc?op=... ──> web_viewer.py ──> combinatorics.py / recurrence.py
   │                                                                      │ (Exact Arbitrary BigInt)
   ├── [Visual Explanations] ──> GET /plot/<op>?... ─> visualizer.py ───> matplotlib (PNG Bytes)
   │
   ├── [Formal Proofs] ───> GET /api/sympy ────────> sympy_tools.py ───> SymPy rsolve & expand
   │
   └── [Unified Audit] ───> GET/POST/DELETE /api/history ──> history_manager.py ──> history.txt
```

### Key API Endpoints
- `GET /api/calc?op=<operation>&<params>`: Evaluates operations via Python backend and returns structured JSON with exact results and step explanations.
- `GET /plot/<operation>?<params>`: Generates and streams PNG image bytes for visual explanations.
- `GET /api/history`: Retrieves history records from `history.txt`.
- `POST /api/history`: Appends calculation records to `history.txt`.
- `DELETE /api/history`: Clears `history.txt`.
- `GET /api/sympy`: Runs formal symbolic checks (rsolve, expansions, limits).

---

## 📁 Project Structure

```
PDL-Mini-Project/
├── combinatorics.py     # Pure math: n!, P, C, derangements, circular perms, multinomials, Pascal
├── recurrence.py        # Sequence generators: Fibonacci, factorial rec, derangements, custom orders
├── visualizer.py        # Matplotlib visual explanations (14 high-resolution chart generators)
├── web_viewer.py        # Local Python HTTP server (serves index.html, /api/calc, /plot/ routes)
├── main.py              # Interactive terminal CLI menu (options 0 to 18)
├── tests.py             # 28 automated plain-function verification unit & API tests
├── sympy_tools.py       # Symbolic verification and closed-form recurrence solver
├── history_manager.py   # Persistent calculation audit log and search engine (history.txt)
├── index.html           # Single-page web app (Dual-engine: Python backend + Offline JS fallback)
├── history.txt          # Saved calculation history records
├── requirements.txt     # Optional libraries (matplotlib, sympy)
├── .gitignore           # Git ignore rules (plots/, __pycache__/)
└── plots/               # Auto-generated demo charts (git-ignored)
```

---

## 🔧 Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| Chart shows "Visual explanation unavailable" | Web server is not running or file was opened via `file://` | Start `python web_viewer.py` and open `http://127.0.0.1:8000` in your browser. |
| `ModuleNotFoundError: No module named 'matplotlib'` | Dependencies not installed in active environment | Run `pip install -r requirements.txt` inside your virtual environment. |
| `[Error] Port 8000 is already in use` | Another process is occupying port 8000 | Run `python web_viewer.py 8001` and open `http://127.0.0.1:8001`. |
| SymPy verification unavailable | SymPy is not installed | Core math, charts, and API work normally without SymPy. To enable formal proofs, run `pip install sympy`. |

---

## 🙋 Quick FAQ for Reviewers

**Q: Do I need an external database or web framework?**  
**A:** No. The project runs purely on Python's built-in standard library (`http.server`) and vanilla HTML5/CSS/JavaScript, requiring zero external server frameworks.

**Q: Can I use the project without running the terminal server?**  
**A:** Yes. Opening `index.html` directly in any web browser gives full access to all calculators via the offline JavaScript BigInt fallback. Running `python web_viewer.py` activates the live Python engine and dynamic visual explanation charts.

**Q: Why are large calculations exact?**  
**A:** Python natively handles arbitrary-precision integers, computing massive numbers like 1000! (2,568 digits) without floating-point rounding errors.

**Q: How do I exit the CLI?**  
**A:** Type `0` at the main menu prompt or press `Ctrl + C`. Both terminate cleanly.

---

Academic Peer Review Project • Python 3.8+ • Matplotlib • Dual-Engine Web Architecture
