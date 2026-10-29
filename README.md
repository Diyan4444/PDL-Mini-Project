# Combinatorial Counting and Permutation Analyzer
Academic Lab Project - Python 3.8+
Name: [YOUR NAME]
Roll No: [YOUR ROLL NO]

===============================================================================
1. OBJECTIVES AND OVERVIEW
===============================================================================
The "Combinatorial Counting and Permutation Analyzer" is a complete, beginner-
readable, mathematically rigorous discrete mathematics tool designed for first-
year university lab submission and viva examination.

The system implements core combinatorics from fundamental principles without
external math libraries, employing exact integer arithmetic throughout. An
optional formal verification module powered by SymPy provides symbolic cross-
checking when available.

Key Capabilities:
- Factorial calculation with cross-verification.
- Ordinary Permutations P(n, r) and Combinations C(n, r).
- Side-by-side P vs C comparison verifying P(n, r) = C(n, r) * r!.
- Permutations with repetition (n^r) and Combinations with repetition (multichoose).
- Multiset permutations using character frequency dictionaries (e.g. MISSISSIPPI).
- Listing of arrangements and groups using tuples and uniqueness validation via sets.
- Verification of binomial identities (Symmetry, Pascal's Identity, Row Sum = 2^n).
- Pascal's Triangle generation with centered visual alignment.
- Linear recurrence relation sequence generation (Fibonacci, Factorial, Custom Order k).
- Binomial expansion of (a*x + b*y)^n into clean ASCII polynomials.
- Optional SymPy symbolic verification and closed-form rsolve solving.
- Persistent audit logging (history.txt) located alongside the module.
- 13-test automated regression test suite.


===============================================================================
2. FOLDER STRUCTURE
===============================================================================
Combinatorial-Counting-and-Permutation-Analyzer/
    main.py              Interactive menu, input validation, display formatting
    combinatorics.py     Factorial, P, C, repetition, multiset, Pascal, identities
    recurrence.py        Fibonacci, factorial recurrence, custom order k recurrence
    sympy_tools.py       Optional SymPy formal verification and rsolve closed form
    history_manager.py   Append-only persistent history logging and search
    tests.py             Plain-function test suite with assertions and reporting
    README.md            Comprehensive documentation, limits, viva QA, demo plan
    requirements.txt     Optional dependency specification (sympy)
    history.txt          Clean calculation log (starts empty)
    screenshots/         Directory for application demonstration captures


===============================================================================
3. INSTALLATION AND EXECUTION
===============================================================================
Requirements:
- Python 3.8 or newer (100% standard library compatible).
- Optional: SymPy (for formal symbolic checks).

Execution Steps:
  1. Open a terminal and navigate to the project directory:
     cd Combinatorial-Counting-and-Permutation-Analyzer

  2. Run the interactive application:
     python main.py

  3. Run the automated test suite directly:
     python tests.py

  4. (Optional) Install SymPy for symbolic verification:
     pip install -r requirements.txt


===============================================================================
4. MODULE RESPONSIBILITIES
===============================================================================
- main.py:
  Provides the central loop, menu coordination (options 0 to 15), strict integer
  input parsing (rejecting letters, decimals, and empty inputs), large-number
  shortening (>60 digits), and clean exit handlers for Ctrl+C and Ctrl+D.

- combinatorics.py:
  Contains mathematical counting logic. All counts are computed using integer
  loops and exact integer division (//). Features multiset counting via frequency
  dictionaries, Pascal's triangle generation, binomial polynomial formatting, and
  itertools arrangement listing stored as tuples and verified with sets.

- recurrence.py:
  Generates numerical sequences for Fibonacci, factorial recurrence, and custom
  linear recurrences of order k (1 <= k <= 5). Rejects zero trailing coefficients.
  Explicitly documents the distinction between numerical generation and closed forms.

- sympy_tools.py:
  Safely imports SymPy under try/except. Checks version and provides optional
  symbolic checks: factorial, binomial, expansion equivalence via simplify(),
  and symbolic closed-form recurrence solving using rsolve() for orders <= 2.

- history_manager.py:
  Manages history.txt located alongside the script via os.path. Replaces delimiter
  pipes with spaces, appends records with timestamps, and handles missing or
  malformed records gracefully.

- tests.py:
  A plain-function verification suite using assert statements (no unittest
  boilerplate). Returns clean [PASS] / [FAIL] output and can be invoked either
  from the command line or via Menu Option 15.


===============================================================================
5. MATHEMATICAL FORMULAS
===============================================================================
1. Factorial:
   n! = n * (n - 1) * ... * 1   (with 0! = 1)

2. Ordinary Permutations (Order Matters):
   P(n, r) = n! // (n - r)!

3. Ordinary Combinations (Order Does NOT Matter):
   C(n, r) = n! // (r! * (n - r)!) = P(n, r) // r!

4. Permutations with Repetition:
   n^r   (Convention: 0^0 = 1; for n=0, r>0 result is 0)

5. Combinations with Repetition (Multichoose / Stars and Bars):
   C(n + r - 1, r)   (For n=0: 1 if r=0 else 0)

6. Multiset Permutations:
   n! // (n1! * n2! * ... * nk!)   where Sum(ni) = n

7. Binomial Identities:
   - Symmetry: C(n, r) = C(n, n - r)
   - Pascal's Additive Rule: C(n, r) = C(n - 1, r - 1) + C(n - 1, r)
   - Row Sum: Sum_{k=0}^{n} C(n, k) = 2^n

8. Binomial Theorem Expansion:
   (a*x + b*y)^n = Sum_{k=0}^{n} C(n, k) * a^(n - k) * b^k * x^(n - k) * y^k

9. Linear Recurrence of Order k:
   a(n) = c1*a(n - 1) + c2*a(n - 2) + ... + ck*a(n - k)


===============================================================================
6. INPUT LIMITS AND BOUNDS
===============================================================================
Operation                   Parameter Limits               Enforcement Reason
-------------------------------------------------------------------------------
Factorial, P, C             n <= 1000, r <= 1000           Prevents text conversion errors
Permutations with Rep.      n <= 1000, r <= 1000           Prevents exponential blowup
Combinations with Rep.      n <= 1000, r <= 1000           Maintains exact arithmetic bounds
Multiset String             Length <= 50 alphanumeric      Maintains dictionary speed
Pascal's Triangle           1 <= rows <= 15                Preserves terminal display alignment
Recurrence Sequence         1 <= terms <= 50               Keeps table output human-readable
Recurrence Order            1 <= order k <= 5              Fits standard linear models
Recurrence Coefficients     |c| <= 1000, c_k != 0          Guarantees true order k
Recurrence Initial Values   |val| <= 1000                  Prevents early integer overflow
Binomial Expansion          0 <= n <= 20, |a|,|b| <= 10    Keeps polynomial legible in console
Arrangement Listing         n <= 8, max 500 items shown    Avoids terminal buffer freeze


===============================================================================
7. KNOWN-ANSWER TEST RESULTS (ACTUAL EXECUTION)
===============================================================================
Test Case                       Expected Value             Actual Output   Status
-------------------------------------------------------------------------------
0!                              1                          1               PASS
1!                              1                          1               PASS
5!                              120                        120             PASS
10!                             3628800                    3628800         PASS
P(5, 3)                         60                         60              PASS
P(5, 0)                         1                          1               PASS
P(5, 5)                         120                        120             PASS
C(5, 3)                         10                         10              PASS
C(52, 5)                        2598960                    2598960         PASS
C(5, 0)                         1                          1               PASS
C(5, 5)                         1                          1               PASS
5^3                             125                        125             PASS
0^0                             1                          1               PASS
C(5 + 3 - 1, 3) = C(7, 3)       35                         35              PASS
Multiset 'MISSISSIPPI'          34650                      34650           PASS
Multiset 'AAB'                  3                          3               PASS
Pascal Row 5                    [1, 5, 10, 10, 5, 1]       Match           PASS
Pascal Row 5 Sum                32                         32              PASS
Fibonacci First 10 Terms        0,1,1,2,3,5,8,13,21,34     Match           PASS
Factorial Recurrence (6 terms)  1,1,2,6,24,120             Match           PASS
Row Sums C(n, k) = 2^n          Verified for n=0..20       Match           PASS
Symmetry C(n, r) = C(n, n - r)  Verified on sample pairs   Match           PASS
Pascal's Additive Rule          Verified on valid n, r     Match           PASS


===============================================================================
8. PYTHON SYLLABUS DEMONSTRATION
===============================================================================
Concept         File & Function                 Specific Pedagogical Role
-------------------------------------------------------------------------------
Tuples          recurrence.py: custom_linear_   Initial values stored as immutable tuples;
                combinatorics.py: list_*        arrangements stored as tuples in itertools.
Sets            combinatorics.py: list_*        Used to verify uniqueness of arrangements
                                                and deduplicate multiset permutations.
Dictionaries    combinatorics.py: multiset_*    Counts character frequencies without losing
                main.py: menu_actions           duplicate letters; routes menu options.
Modules         combinatorics.py, recurrence.py Separates algorithms, persistence, tests,
                sympy_tools.py, history_manager and user interface cleanly.
File Handling   history_manager.py: save/read   Appends and parses persistent history.txt
                                                using explicit UTF-8 encoding and os.path.
Loops & Cond.   combinatorics.py: factorial     Iterative product loops; row building;
                main.py: main()                 interactive while loop with boundary checks.
Exception       main.py: get_integer_input      Catches ValueError, KeyboardInterrupt,
Handling        sympy_tools.py                  EOFError; catches ImportError for SymPy.


===============================================================================
9. VIVA VOCE EXAMINATION QUESTIONS AND ANSWERS
===============================================================================

Q1: What is the fundamental difference between a permutation and a combination?
A1: Order. In permutations, the sequence of selection matters (e.g., (A, B) and
    (B, A) are two distinct permutations). In combinations, order does not matter;
    only the membership of the subset counts (e.g., {A, B} is the same single group).

Q2: Why is 0! mathematically defined as 1?
A2: Combinatorially, 0! represents the number of ways to arrange an empty set of
    zero objects, which can be done in exactly 1 way (the empty arrangement).
    Algebraically, the recurrence n! = n * (n - 1)! for n = 1 gives 1! = 1 * 0!,
    which requires 0! = 1 for mathematical consistency.

Q3: How do permutations with repetition differ from ordinary permutations?
A3: In ordinary permutations P(n, r), once an item is placed, it cannot be picked
    again (sampling without replacement), requiring r <= n. In permutations with
    repetition (n^r), items can be reused indefinitely (sampling with replacement),
    allowing r > n.

Q4: How do combinations with repetition work conceptually?
A4: Combinations with repetition count the number of ways to select r elements from
    n types where elements of the same type can be chosen multiple times. This is
    formulated using the Stars and Bars theorem as C(n + r - 1, r), representing
    r items (stars) separated by (n - 1) dividers (bars).

Q5: Why must character frequencies be counted with a dictionary in multiset permutations?
A5: In a word like MISSISSIPPI, identical letters produce indistinguishable orderings.
    A dictionary maps each unique character to its exact count. Dividing n! by the
    product of factorials of each character's count cancels out the duplicate
    permutations.

Q6: Why is converting input directly to a set dangerous for repeated objects?
A6: Converting a string directly to a set (e.g. set("MISSISSIPPI")) strips all duplicate
    characters, leaving only {'M', 'I', 'S', 'P'} and losing the multiplicity required
    to calculate the denominator factorials.

Q7: What is Pascal's identity, and how does it relate to Pascal's triangle?
A7: Pascal's identity states C(n, r) = C(n - 1, r - 1) + C(n - 1, r). It proves that
    every interior entry in Pascal's triangle is the sum of the two numbers directly
    above it in the previous row.

Q8: What is a recurrence relation, and how does numerical generation differ from a closed form?
A8: A recurrence relation defines each term of a sequence as a function of preceding
    terms (e.g. F(n) = F(n-1) + F(n-2)). Numerical generation computes terms sequentially
    one by one. A closed-form expression calculates a(n) directly for any n in O(1)
    without computing intermediate terms.

Q9: Why must integer division (//) be used instead of floating-point division (/)?
A9: Floating-point division converts numbers to 64-bit IEEE-754 floats, which have
    only 53 bits of precision (approx. 15-17 decimal digits). Combinatorial numbers
    rapidly exceed this limit, causing truncation and rounding inaccuracies. Python's
    integer division (//) supports arbitrary precision with zero loss.

Q10: Why do input limits (e.g. n <= 1000, rows <= 15) exist?
A10: Large inputs can create gigantic numbers that take excessive time to compute or
     exceed Python 3.11+'s 4,300-digit limit for integer-to-string conversion. The caps
     ensure responsiveness and prevent terminal crashes while exceeding normal lab needs.

Q11: Why is itertools used only for listing and never for counting?
A11: Listing generates all actual items in memory, which is O(n!) or O(n^r) in memory
     and time. Counting uses closed formulas that run in O(n) or O(r) time with O(1)
     memory. The listing function demonstrates concrete subsets, but counting relies
     on the mathematical formula.

Q12: Why is the project partitioned into distinct modules?
A12: Modularity separates concerns: combinatorics.py contains pure math, recurrence.py
     handles sequences, history_manager.py isolates file I/O, sympy_tools.py isolates
     optional third-party tools, tests.py automates quality control, and main.py
     manages the user interface.

Q13: How does the application ensure robust file handling for history.txt?
A13: It resolves history.txt relative to the module file path via os.path.dirname(
     os.path.abspath(__file__)), guaranteeing it functions regardless of the current
     working directory. It also sanitizes inputs to eliminate delimiter conflicts.

Q14: How are keyboard interruptions (Ctrl+C, Ctrl+D) handled?
A14: The input helper wraps raw input calls in try/except blocks catching KeyboardInterrupt
     and EOFError, printing a polite goodbye and exiting with sys.exit(0) without tracebacks.

Q15: What is SymPy's role, and what happens if it is not installed?
A15: SymPy provides optional formal symbolic verification. If not installed, it is
     caught cleanly by try/except ImportError, displaying an informational note while
     all core combinatorial and recurrence features remain 100% operational.

Q16: Why is closed-form recurrence solving restricted to orders <= 2 with constant coefficients?
A16: Linear recurrences of order 1 and 2 with constant coefficients possess standard
     characteristic polynomial roots that can be reliably solved in closed form. Factorial
     recurrence a(n) = n*a(n-1) has variable coefficients, and higher-order equations
     frequently produce intractable roots.


===============================================================================
10. FIVE-TO-SEVEN MINUTE LAB DEMO PLAN
===============================================================================
Minute 1: Introduction and Self-Test
  - Launch application: python main.py
  - Select Option 15: Run self-test. Point out that all 13 automated tests pass
    immediately, proving mathematical correctness.

Minute 2: Core Permutations vs Combinations
  - Select Option 4: Permutation vs Combination comparison.
  - Enter n = 5, r = 3. Show P(5, 3) = 60, C(5, 3) = 10, r! = 6.
  - Explain the identity P = C * r! and point out the sample letter permutations.

Minute 3: Multiset and Repeated Elements
  - Select Option 7: Multiset arrangements.
  - Enter "MISSISSIPPI". Show how the frequency dictionary is constructed
    and how 11!/(1!*4!*4!*2!) yields 34,650.

Minute 4: Pascal's Triangle & Binomial Expansion
  - Select Option 10: Pascal's triangle for 6 rows. Point out Row 5 (1 5 10 10 5 1).
  - Select Option 12: Binomial expansion for (2*x - 3*y)^2 or (x + y)^3. Show the
    generated ASCII polynomial and SymPy verification check.

Minute 5: Recurrence & SymPy Closed Form
  - Select Option 11: Fibonacci sequence for 10 terms (0, 1, 1, ..., 34).
  - Select Option 13: SymPy rsolve check for Fibonacci to display the symbolic
    Binet formula.

Minute 6: History & Graceful Exit
  - Select Option 14: View history log to demonstrate persistence across runs.
  - Select Option 0: Clean exit. Demonstrate Ctrl+C graceful termination.


===============================================================================
11. CAPTURING DEMO SCREENSHOTS
===============================================================================
To capture genuine screenshots for lab documentation:
1. Main Menu: Run python main.py and capture the welcome screen and menu list.
2. Comparison: Run Option 4 with n=4, r=3 showing orderings of sample letters.
3. Multiset: Run Option 7 with word "MISSISSIPPI".
4. Pascal's Triangle: Run Option 10 with 6 rows.
5. Binomial Expansion: Run Option 12 with n=3, a=1, b=1 showing SymPy check.
6. History & Tests: Run Option 15 (self-test) and Option 14 (history view).
Save captures into the 'screenshots/' directory as PNG images.
