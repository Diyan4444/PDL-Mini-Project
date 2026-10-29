# 🎲 Combinatorial Counting & Permutation Analyzer

A smart, interactive math exploration tool designed for college students and peer reviewers. It helps you understand and calculate **Permutations, Combinations, Anagrams (Multisets), Pascal's Triangle, and Sequence Patterns** with step-by-step explanations.

You can use it either as a **visual Web App in your browser (Google Chrome)** or as an **interactive Terminal program in VS Code**.

---

## 💡 What is This Project About?

Have you ever wondered:
- *In how many ways can 5 runners finish in 1st, 2nd, and 3rd place?* &rarr; **Permutations $P(n, r)$**
- *How many different 3-person project teams can you pick from 10 classmates?* &rarr; **Combinations $C(n, r)$**
- *Why does order matter when picking a passcode, but not when picking lottery numbers?* &rarr; **P vs C Comparison**
- *How many unique words can you make by rearranging the letters in `"MISSISSIPPI"`?* &rarr; **Multisets**
- *What pattern connects Pascal's Triangle to $(x + y)^n$ algebra?* &rarr; **Binomial Expansion**

This project solves all these questions step-by-step, using exact integer arithmetic (no decimal rounding errors) and clear human explanations!

---

## 🚀 Getting Started in VS Code (Step-by-Step)

You don't need any complex setup. Follow these quick steps to get it running on your PC:

### Step 1: Clone the Repository
Open your **VS Code terminal** (`Ctrl + \`` or `Terminal` &rarr; `New Terminal`) and run:

```bash
git clone https://github.com/Diyan4444/PDL-Mini-Project.git
cd PDL-Mini-Project
```

---

## 🎮 How to Run and Explore

You have **two easy ways** to use the project:

### Option A: Open the Interactive Web App (Recommended! 🌐)
No servers or Python packages needed! Just open the visual webpage:
1. In the VS Code file explorer on the left, locate **`index.html`**.
2. **Right-click `index.html`** &rarr; select **"Reveal in File Explorer"**.
3. **Double-click `index.html`** (or right-click &rarr; *Open with Google Chrome*).
4. Enjoy the clean, interactive dashboard with buttons, live calculations, and visual diagrams!

---

### Option B: Run in the Terminal (Python CLI 💻)
If you prefer running it from the command line:
```bash
python main.py
```
* A numbered menu (0 to 15) will appear.
* Type a number (like `4` for comparison or `10` for Pascal's triangle) and press `Enter`.
* Press `0` anytime to exit cleanly.

---

### Option C: Run the Automated Self-Test Suite (🧪)
To verify that all math formulas are 100% accurate:
```bash
python tests.py
```
You will see 13 automated tests pass with green `[PASS]` tags!

---

## ✨ Key Features at a Glance

| # | Feature | What It Does (In Simple Words) |
|---|---|---|
| **1** | **Factorial ($n!$)** | Multiplies numbers down to 1 (e.g. $5! = 5 \times 4 \times 3 \times 2 \times 1 = 120$). Also shows why $0! = 1$. |
| **2** | **Permutations $P(n, r)$** | Counts arrangements where **order matters** (like podium finishes or phone PINs). |
| **3** | **Combinations $C(n, r)$** | Counts selections where **order does NOT matter** (like choosing card hands or team members). |
| **4** | **P vs C Comparison** | Shows side-by-side why $P = C \times r!$ using sample letters like `A, B, C`. |
| **5** | **Permutations with Repetition** | Calculates $n^r$ when options can be reused (like a 4-digit lock with digits 0-9). |
| **6** | **Combinations with Repetition** | "Stars & Bars" counting (like picking 3 ice cream scoops from 5 available flavors). |
| **7** | **Multiset Word Anagrams** | Counts distinct letter rearrangements for words with repeats (e.g. `MISSISSIPPI = 34,650`). |
| **8** | **List Arrangements** | Actually prints out all the combinations/permutations for small inputs and checks uniqueness with Sets. |
| **9** | **Binomial Identities** | Verifies core math rules: Symmetry $C(n,r) = C(n, n-r)$ and Row Sum $= 2^n$. |
| **10** | **Pascal's Triangle** | Generates the classic number pyramid where each number is the sum of the two above it. |
| **11** | **Recurrence Sequences** | Generates sequence terms for Fibonacci ($0, 1, 1, 2, 3, 5\dots$) or custom step rules. |
| **12** | **Binomial Theorem Expansion** | Multiplies out algebraic expressions like $(2x - 3y)^3$ into clean polynomial text. |
| **13** | **Symbolic Verification** | Explains closed-form math and compares results with the SymPy math library. |
| **14** | **Calculation History** | Keeps an audit log of all your past calculations so you never lose your work. |
| **15** | **Automated Self-Test** | Instant 13-test quality assurance checker. |

---

## 📁 Project Structure (What Each File Does)

```
PDL-Mini-Project/
├── index.html           # 🌟 Visual Web Application (Double-click to open in Chrome!)
├── main.py              # Terminal menu and interactive CLI coordination
├── combinatorics.py     # Pure math formulas (Factorial, P, C, Multisets, Pascal)
├── recurrence.py        # Sequence generators (Fibonacci, step recurrences)
├── sympy_tools.py       # Optional symbolic formal verification
├── history_manager.py   # Handles saving and reading calculation history (history.txt)
├── tests.py             # 13 assertion-based unit tests
├── history.txt          # Saved calculation log
└── requirements.txt     # Optional libraries (sympy)
```

---

## 🙋 Quick FAQ for Reviewers

**Q: Do I need to install any heavy packages or databases?**  
**A:** No! The project runs using standard Python 3 (comes pre-installed with everything needed). No external databases or frameworks are required.

**Q: What if I don't want to use the terminal?**  
**A:** Simply double-click **`index.html`**! It runs completely in your web browser with a full graphical interface.

**Q: How do I exit the terminal program?**  
**A:** Enter `0` in the menu, or press `Ctrl + C` anytime. The program will exit gracefully without error messages.

---

*Academic Peer Review Project • Python 3.8+ & Modern Web UI*
