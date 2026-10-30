# 🎲 Combinatorial Counting & Permutation Analyzer

A smart, interactive math exploration and visualization tool designed for college students and peer reviewers. It computes and demonstrates **Permutations, Combinations, Anagrams (Multisets), Pascal's Triangle, Recurrence Relations, and Binomial Expansions** with step-by-step arithmetic. Every one of operations 1 to 12 now dynamically generates a Matplotlib "Visual Explanation" chart directly beneath the result, helping students see *why* the mathematical formulas work.

---

## ⚡ Three Ways to Use It

- **Web App with Live Charts (Recommended):** Run `python web_viewer.py` → open http://127.0.0.1:8000
- **Terminal CLI:** Run `python main.py` (interactive menu with options 0 to 16)
- **Standalone Browser File:** Double-click `index.html` (calculators work offline; Python charts do not appear)

---

## 💡 What is This Project About?

Have you ever wondered:
- *In how many ways can 5 runners finish in 1st, 2nd, and 3rd place?* → **Permutations P(n, r)**
- *How many different 3-person project teams can you pick from 10 classmates?* → **Combinations C(n, r)**
- *Why does order matter when picking a passcode, but not when picking lottery numbers?* → **P vs C Comparison**
- *How many unique words can you make by rearranging the letters in "MISSISSIPPI"?* → **Multisets**
- *What pattern connects Pascal's triangle to (x + y)^n algebra?* → **Binomial Expansion**

This project answers these questions using exact Python integer arithmetic (zero decimal rounding error) and pairs every calculation with a clear, visual explanation.

---

## 🔍 Why Not Just Google the Answer?

Search engines and calculators give a final number, but they do not show the mathematical reasoning behind it. This tool displays the full step-by-step working and generates a synchronized chart showing slot choices, combination collapse, stars-and-bars partitions, and Pascal triangle structures.

---

## 📦 Installation & Setup

**Prerequisite:** Python 3.8+ (`python --version`, or `python3` / `py` on some systems).

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
- `matplotlib`: Generates the 12 dynamic visual explanation charts.
- `sympy`: Optional dependency used only for formal symbolic verification (Option 13).
- *Core mathematics and the web server use only the Python standard library.*

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
2. **Try it:** Open **Factorial**, enter `720`, and click **Calculate**. The exact 1,747-digit result appears alongside a logarithmic growth chart. Change the input to `4`, then `5` — the chart updates live for each calculation.
3. **Stop server:** Press `Ctrl + C` in the terminal to stop cleanly.
4. **Port in use:** Run `python web_viewer.py 8001` and open http://127.0.0.1:8001.

> **Note:** The server listens only on `127.0.0.1` (your local computer, never exposed to external networks). You must open `http://127.0.0.1:8000` in the browser; double-clicking `index.html` runs offline calculations without live charts.

---

## 💻 Terminal CLI (python main.py)

Run the full interactive command-line interface:
```bash
python main.py
```
- Features a clean numeric menu (options 1 to 16, and `0` to exit).
- After running any of operations 1 to 12, enter `1` at the visual prompt to view the generated chart.
- **Option 16:** Batch-generates all 12 demo explanation charts into the `plots/` folder (git-ignored).
- Operations 13 to 15 (SymPy verification, history log, and self-test) run purely in text mode without charts.

---

## 🧪 Run the Automated Tests

Verify mathematical accuracy, input validation, and server endpoints:
```bash
python tests.py
```
**Test Result:** All **22/22 tests passed** (0 failed).  
The suite validates known mathematical answers, repetition variants, multiset arrangements, identities, Pascal construction, recurrence sequences, error rejection, history persistence, SymPy integration, and dynamic HTTP `/plot/` endpoints. Visualizer file-creation tests skip cleanly if Matplotlib is absent.

---

## 📊 Key Features Table

| # | Feature | What It Does | Visual Explanation |
|---|---|---|---|
| **1** | Factorial n! | Exact integer product down to 1 | Log10 growth curve and multiplication chain strip |
| **2** | Permutations P(n, r) | Ordered arrangements (order matters) | Shrinking choice slots diagram and distribution curve |
| **3** | Combinations C(n, r) | Unordered selections (order does not matter) | Symmetric bell curve and r! subset arrangement collapse |
| **4** | P vs C Comparison | Proves that P(n, r) = C(n, r) * r! | Side-by-side grouped bars comparing ordered vs unordered |
| **5** | Permutations with Repetition | Sequence counting with replacement (n^r) | Constant choice slots vs shrinking permutation slots |
| **6** | Combinations with Repetition | Multichoose selections C(n+r-1, r) | Stars-and-bars divider model with item buckets |
| **7** | Multiset Arrangements | Anagram counting with repeated letters | Letter frequency histogram and duplicate factorial divisions |
| **8** | List Small Arrangements | Generates actual tuples and verifies uniqueness | Arrangement badge grid with uniqueness verification card |
| **9** | Binomial Identities | Proves symmetry, Pascal's rule, and sum = 2^n | Three panels: symmetry, Pascal addition, and row sum |
| **10** | Pascal's Triangle | Centered arithmetic triangle row by row | Number pyramid with odd/even Sierpinski parity colouring |
| **11** | Recurrence Relations | Solves Fibonacci, factorial, and custom recurrences | Step progression and Golden Ratio (phi ≈ 1.618) convergence |
| **12** | Binomial Expansion | Expands (a*x + b*y)^n into clean algebraic text | Signed polynomial coefficients and underlying Pascal row |
| **13** | SymPy Verification | Formal algebraic cross-check and rsolve | None |
| **14** | Calculation History | Audit log with search and timestamp persistence | None |
| **15** | Automated Self-Test | Automated verification suite across all modules | None |
| **16** | Visual Gallery | Batch-generates all 12 demo charts into plots/ | Generates all 12 explanation charts |

---

## 🧩 How the Pieces Fit Together

```
Browser (index.html) → GET /plot/<operation>?params → web_viewer.py validates → visualizer.py draws (matplotlib) → PNG bytes returned → shown under result
```

### Dynamic Plot HTTP Endpoints
| Endpoint | Query Parameters | Description |
|---|---|---|
| `/plot/factorial` | `n` (0..1000) | Factorial growth curve & multiplication chain |
| `/plot/permutations` | `n`, `r` (0..1000, r <= n) | Permutation slots and distribution |
| `/plot/combinations` | `n`, `r` (0..1000, r <= n) | Combination symmetry & r! collapse |
| `/plot/comparison` | `n`, `r` (0..1000, r <= n) | Side-by-side grouped bar comparison |
| `/plot/permrep` | `n`, `r` (0..1000) | Constant choice slots (n^r) |
| `/plot/combrep` | `n`, `r` (0..1000) | Stars-and-bars partition diagram |
| `/plot/multiset` | `word` (alphanumeric, max 50) | Duplicate letter frequencies & divisions |
| `/plot/listing` | `mode` (perm/comb/multi), `n`, `r`, `word` | Arrangement tiles (n <= 8) |
| `/plot/identities` | `n`, `r` (0..1000, r <= n) | 3-panel identity proof |
| `/plot/pascal` | `rows` (1..15) | Number pyramid and parity colouring |
| `/plot/recurrence` | `type` (fib/fact/custom), `terms` (1..50), `order`, `coeffs`, `inits` | Step progression and ratio convergence |
| `/plot/expansion` | `n` (0..20), `a`, `b` (-10..10) | Polynomial coefficients & Pascal row |

---

## 📁 Project Structure

```
PDL-Mini-Project/
├── combinatorics.py     # Pure math functions (n!, P, C, multisets, Pascal, expansions)
├── recurrence.py        # Sequence generators (Fibonacci, factorial, custom recurrences)
├── visualizer.py        # Matplotlib visual explanations (12 chart generators)
├── web_viewer.py        # Local Python HTTP server (serves index.html and /plot/ routes)
├── main.py              # Terminal interactive CLI menu (options 0-16)
├── tests.py             # 22 automated plain-function verification tests
├── sympy_tools.py       # Optional symbolic formal verification
├── history_manager.py   # Calculation logging and search engine (history.txt)
├── index.html           # Single-page web interface with live visual charts
├── history.txt          # Saved calculation history log
├── requirements.txt     # Optional libraries (matplotlib, sympy)
├── .gitignore           # Git ignore rules (plots/, __pycache__/)
└── plots/               # Auto-generated demo charts (git-ignored)
```

---

## 🔧 Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| Chart does not appear / "Visual explanation unavailable" | Web server is not running or file was opened via `file://` | Start `python web_viewer.py` and open `http://127.0.0.1:8000` in your browser. |
| `ModuleNotFoundError: No module named 'matplotlib'` | Dependencies not installed in active environment | Run `pip install -r requirements.txt` inside your virtual environment. |
| `[Error] Port 8000 is already in use` | Another process is using port 8000 | Run `python web_viewer.py 8001` and navigate to `http://127.0.0.1:8001`. |
| "Coefficients and initial values must have absolute value <= 1000" | Custom recurrence inputs exceed chart safety limit | Use initial values and coefficients between -1000 and 1000 for visual charts. |
| SymPy verification unavailable | SymPy is not installed | Core math and charts work normally without SymPy. To enable Option 13, run `pip install sympy`. |

---

## 🙋 Quick FAQ for Reviewers

**Q: Do I need an external database or web framework?**  
**A:** No. The project runs purely on Python's built-in standard library (`http.server`) and vanilla JavaScript, requiring zero external frameworks.

**Q: Can I use the project without the terminal?**  
**A:** Yes. Opening `index.html` directly gives full access to all calculators offline. Starting `python web_viewer.py` adds live dynamic charts.

**Q: Why are large calculations exact?**  
**A:** Python natively supports arbitrary-precision integers, computing large values like 1000! (2,568 digits) without rounding errors.

**Q: How do I exit the CLI?**  
**A:** Type `0` at the menu prompt or press `Ctrl + C`. Both terminate cleanly without tracebacks.

---

Academic Peer Review Project • Python 3.8+ • Matplotlib • Modern Web UI
