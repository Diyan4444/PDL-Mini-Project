# Project: Combinatorial Counting and Permutation Analyzer
# Group Members (Name - Roll No):
#   Dheer Chheda      - 251080019
#   Diyan Shah        - 251080020
#   Aryan Adivarekar  - 251080008
#   Advait Deodhar    - 251080018
#
# Matplotlib charts that explain each result visually.
# Every plot_* function either saves a PNG into plots/ and returns its path (used by the CLI),
# or returns the PNG bytes when called with as_bytes=True (used by the web server).
# If matplotlib is not installed they all return None and the rest of the app keeps working.

import os
import io
import math
import datetime
import threading
import functools

import combinatorics
import recurrence

try:
    import matplotlib
    # "Agg" draws straight to image files without opening a window, so it also works
    # inside the web server. It must be selected before pyplot is imported.
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import patches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# pyplot is not thread-safe and the web server handles requests on several threads,
# so only one chart is drawn at a time.
PLOT_LOCK = threading.Lock()
PLOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plots")

# Colours mean the same thing on every chart: blue = ordered (permutations),
# green = unordered (combinations), orange = the value the user chose, red = negative.
BLUE = "#1f77b4"
GREEN = "#2ca02c"
ORANGE = "#ff7f0e"
GRAY = "#94a3b8"
RED = "#d62728"
DARK = "#0f172a"
MUTED = "#475569"
BOLD = {"fontsize": 10, "fontweight": "bold"}
TITLE = {"fontsize": 11, "fontweight": "bold"}


def log10(value):
    # Most charts use a log10 scale because counts like 1000! have thousands of digits.
    # math.log10 accepts huge ints directly (no float overflow). A count of 0 is drawn as 0.
    return math.log10(value) if value > 0 else 0.0


def sample_k(n, highlight=None, limit=25):
    # k values for a bar chart over 0..n. For large n, about `limit` evenly spaced values
    # are used so bars stay readable; n itself and the highlighted value are always kept.
    if n <= limit:
        return list(range(n + 1))
    values = set(range(0, n + 1, n // limit)) | {n}
    if highlight is not None:
        values.add(highlight)
    return sorted(values)


def bars(ax, labels, values, colors, xlabel=None, ylabel=None, title=None, width=0.6):
    ax.bar([str(v) for v in labels], values, color=colors, width=width, edgecolor=DARK, linewidth=0.5)
    if xlabel:
        ax.set_xlabel(xlabel, **BOLD)
    if ylabel:
        ax.set_ylabel(ylabel, **BOLD)
    if title:
        ax.set_title(title, **TITLE)
    ax.grid(axis="y", linestyle="--", alpha=0.5)


def box(ax, x, y, w, h, face, edge, lw=1.5, pad=0.08):
    ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad={pad}", facecolor=face, edgecolor=edge, linewidth=lw))


def message(ax, title, text, edge=BLUE):
    ax.axis("off")
    ax.set_title(title, pad=12, **TITLE)
    ax.text(0.5, 0.5, text, ha="center", va="center", fontsize=11, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.6", facecolor="#eff6ff", edgecolor=edge))


def chart(func):
    # Decorator shared by every plot_* function. The plot function only builds the figure
    # and returns (figure, caption); this wrapper handles the rest: the matplotlib check,
    # the lock, the caption, the layout, saving or returning the PNG, and always closing
    # the figure so memory is freed even if saving fails.
    @functools.wraps(func)
    def wrapper(*args, as_bytes=False, **kwargs):
        if not MATPLOTLIB_AVAILABLE:
            return None
        with PLOT_LOCK:
            fig, caption = func(*args, **kwargs)
            fig.text(0.5, 0.02, "What you are looking at: " + caption, ha="center", va="bottom",
                     fontsize=8.5, style="italic", color="#334155", wrap=True)
            # Keep the bottom 5% free so the caption does not overlap the axis labels.
            fig.tight_layout(rect=(0, 0.05, 1, 1))
            try:
                if as_bytes:
                    buffer = io.BytesIO()
                    fig.savefig(buffer, format="png", dpi=120)
                    return buffer.getvalue()
                os.makedirs(PLOTS_DIR, exist_ok=True)
                stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                path = os.path.join(PLOTS_DIR, f"{func.__name__}_{stamp}.png")
                fig.savefig(path, dpi=120)
                return path
            finally:
                plt.close(fig)
    return wrapper


@chart
def plot_factorial(n):
    value = combinatorics.factorial(n)
    ks = sample_k(n)
    logs = [log10(math.factorial(k)) for k in ks]

    # Small n also gets a "x 1 = 1, x 2 = 2, x 3 = 6 ..." multiplication strip above the bars.
    if n <= 8:
        fig, (ax_chain, ax) = plt.subplots(2, 1, figsize=(8.5, 6.5), gridspec_kw={"height_ratios": [1, 2]})
        ax_chain.axis("off")
        ax_chain.set_xlim(-0.5, max(1, n) + 0.5)
        ax_chain.set_ylim(0, 3)
        ax_chain.set_title(f"Multiplication Chain for {n}!", pad=8, **TITLE)
        if n == 0:
            ax_chain.text(0.5, 1.5, "0! = 1 (exactly 1 empty arrangement)", ha="center", va="center", fontsize=11,
                          fontweight="bold", bbox=dict(boxstyle="round,pad=0.5", facecolor="#e2e8f0", edgecolor="#64748b"))
        running = 1
        for i in range(1, n + 1):
            running *= i
            x = i - 0.5
            box(ax_chain, x - 0.35, 0.8, 0.7, 1.4, "#eff6ff", BLUE, pad=0.1)
            ax_chain.text(x, 1.7, f"x {i}", ha="center", va="center", **BOLD)
            ax_chain.text(x, 1.1, f"= {running}", ha="center", va="center", fontsize=8.5, color="#334155")
    else:
        fig, ax = plt.subplots(figsize=(8.5, 5.5))

    colors = [ORANGE if k == n else BLUE for k in ks]
    bars(ax, ks, logs, colors, "Integer k", "log10( k! )", f"Super-Exponential Growth of Factorials (k = 0 to {n})", 0.65)
    last = ax.patches[-1]
    ax.annotate(f"{len(str(value))} digits", xy=(last.get_x() + last.get_width() / 2, last.get_height()),
                xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold", color="#b45309")
    return fig, "each integer multiplies the previous total, so factorials grow super-exponentially."


@chart
def plot_permutations(n, r):
    # Called only to validate n and r: raises ValueError if r > n.
    combinatorics.permutations(n, r)
    fig, (ax_slots, ax) = plt.subplots(2, 1, figsize=(9.0, 7.0), gridspec_kw={"height_ratios": [1.1, 1.8]})
    ax_slots.axis("off")
    ax_slots.set_title(f"Choice Slots Diagram for P({n}, {r})", pad=8, **TITLE)

    if r == 0:
        ax_slots.text(0.5, 0.5, "0 slots to fill: exactly 1 empty arrangement [P(n, 0) = 1]", ha="center", va="center", **BOLD)
    else:
        # One box per slot showing how many choices are left. With more than 8 slots,
        # show the first four, "..." (None), then the last two.
        slots = list(range(1, r + 1)) if r <= 8 else [1, 2, 3, 4, None, r - 1, r]
        width, gap = 0.8, 0.25
        total = len(slots) * width + (len(slots) - 1) * gap
        running = 1
        for idx, slot in enumerate(slots):
            x = -total / 2 + idx * (width + gap)
            centre = x + width / 2
            if slot is None:
                ax_slots.text(centre, 0.5, ". . .", ha="center", va="center", fontsize=14, fontweight="bold")
                continue
            choices = n - slot + 1
            running *= choices
            box(ax_slots, x, 0.1, width, 0.8, "#eff6ff", BLUE)
            ax_slots.text(centre, 0.72, f"Slot {slot}", ha="center", va="center", fontsize=8, color="#64748b", fontweight="bold")
            ax_slots.text(centre, 0.48, f"{choices} choices", ha="center", va="center", fontsize=9.5, fontweight="bold")
            if r <= 8:
                ax_slots.text(centre, 0.22, f"Running: {running}", ha="center", va="center", fontsize=7.5, color="#1e3a8a")
        ax_slots.set_xlim(-total / 2 - 0.5, total / 2 + 0.5)
        ax_slots.set_ylim(-0.2, 1.2)

    ks = sample_k(n, r)
    bars(ax, ks, [log10(math.perm(n, k)) for k in ks], [ORANGE if k == r else BLUE for k in ks],
         "Selection Size k", "log10( P(n, k) )", f"P({n}, k) for k = 0..{n} (orange = chosen r = {r})", 0.65)
    return fig, "each slot has one fewer choice because items cannot be reused; the total is the product of the choices."


@chart
def plot_combinations(n, r):
    # Called only to validate n and r. Small inputs get a second panel showing how
    # the r! orderings of one group collapse into a single combination.
    combinatorics.combinations(n, r)
    if n <= 6 and r >= 1:
        fig, (ax, ax_collapse) = plt.subplots(1, 2, figsize=(10.0, 5.2), gridspec_kw={"width_ratios": [1.2, 1.0]})
    else:
        fig, ax = plt.subplots(figsize=(8.5, 5.2))
        ax_collapse = None

    ks = sample_k(n, r)
    bars(ax, ks, [log10(math.comb(n, k)) for k in ks], [ORANGE if k == r else GREEN for k in ks],
         "Subset Size k", "log10( C(n, k) )", f"Combinations C({n}, k) [Symmetric Bell Shape]", 0.65)
    if n == 0:
        ax.set_ylim(0, 1)

    if ax_collapse is not None:
        letters = combinatorics.LETTERS[:r]
        orderings = ["".join(p) for p in combinatorics.list_letter_permutations(r, r)[0]]
        ax_collapse.axis("off")
        ax_collapse.set_title("The 'Collapse' Effect: P / r! = C", pad=8, **TITLE)
        box(ax_collapse, 0.05, 0.08, 0.90, 0.84, "#f0fdf4", GREEN, lw=2.0, pad=0.05)
        ax_collapse.text(0.5, 0.84, "ONE COMBINATION SET", ha="center", va="center", fontsize=10, fontweight="bold", color="#166534")
        ax_collapse.text(0.5, 0.75, "{" + ", ".join(letters) + "}", ha="center", va="center", fontsize=12, fontweight="bold")
        ax_collapse.text(0.5, 0.63, f"Contains all {r}! = {len(orderings)} orderings:", ha="center", va="center", fontsize=8.5, color=MUTED)
        shown = ",  ".join(orderings[:12]) + (f"\n... + {len(orderings) - 12} more" if len(orderings) > 12 else "")
        ax_collapse.text(0.5, 0.40, shown, ha="center", va="center", fontsize=9.5, fontfamily="monospace",
                         bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#cbd5e1"))
        ax_collapse.text(0.5, 0.16, f"Dividing by {r}! cancels these repeated orderings.", ha="center", va="center",
                         fontsize=8.5, style="italic", color="#166534")
    return fig, "combinations ignore order; dividing P(n, r) by r! collapses every group of r! orderings into one subset."


@chart
def plot_comparison(n, r):
    p, c, rf = combinatorics.permutations(n, r), combinatorics.combinations(n, r), math.factorial(r)
    fig, (ax, ax_decomp) = plt.subplots(1, 2, figsize=(10.5, 5.2), gridspec_kw={"width_ratios": [1.4, 1.0]})

    # Left: P(n, k) and C(n, k) side by side for each k. Right: the three numbers in P = C * r!.
    ks = list(range(min(n, 15) + 1))
    w = 0.38
    ax.bar([k - w / 2 for k in ks], [log10(math.perm(n, k)) for k in ks], width=w, label="P(n, k) [Ordered]", color=BLUE, edgecolor=DARK, linewidth=0.5)
    ax.bar([k + w / 2 for k in ks], [log10(math.comb(n, k)) for k in ks], width=w, label="C(n, k) [Unordered]", color=GREEN, edgecolor=DARK, linewidth=0.5)
    ax.set_xticks(ks)
    ax.set_xlabel("Selection Size k", **BOLD)
    ax.set_ylabel("log10( Count )", **BOLD)
    ax.set_title(f"Permutations vs Combinations (n = {n})", **TITLE)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    ok = p == c * rf
    bars(ax_decomp, [f"C({n},{r})", f"{r}!", f"P({n},{r})"], [log10(c), log10(rf), log10(p)], [GREEN, GRAY, BLUE],
         ylabel="log10( Value )", width=0.55)
    ax_decomp.set_title(f"P = C x r! [{'VERIFIED MATCH' if ok else 'FAILED'}]", color="#15803d" if ok else "#b91c1c", **TITLE)
    if p == 1:
        ax_decomp.set_ylim(0, 1)
    return fig, "permutations exceed combinations by a factor of r!, the number of orderings inside each subset."


@chart
def plot_perm_with_repetition(n, r):
    total = combinatorics.permutations_with_repetition(n, r)
    # Small inputs draw the full choice tree (at most 4^3 = 64 leaves);
    # larger ones compare the growth of n^k with P(n, k) instead.
    if 0 < n <= 4 and 0 < r <= 3:
        fig, ax = plt.subplots(figsize=(9.5, 6.0))
        ax.axis("off")
        ax.set_title(f"Choice Tree: {n}^{r} = {total} Sequences", pad=12, **TITLE)

        def position(level, index):
            # Spread the n^level nodes of a tree level evenly across the width (0 to 10).
            return (index + 0.5) * 10.0 / n ** level, 1.0 - level / (r + 0.5)

        ax.scatter([5.0], [1.0], color=DARK, s=80, zorder=5)
        ax.text(5.0, 1.04, "Start", ha="center", va="bottom", fontsize=8.5, fontweight="bold")
        for level in range(1, r + 1):
            for parent in range(n ** (level - 1)):
                px, py = position(level - 1, parent) if level > 1 else (5.0, 1.0)
                for branch in range(n):
                    cx, cy = position(level, parent * n + branch)
                    ax.plot([px, cx], [py, cy], color=GRAY, lw=1.2, zorder=3)
                    ax.scatter([cx], [cy], color=ORANGE if level == r else BLUE, s=50, zorder=5)
                    if level <= 2:
                        ax.text((px + cx) / 2, (py + cy) / 2 + 0.02, str(branch + 1), fontsize=7.5, color="#1e3a8a", ha="center")
        ax.set_xlim(-0.5, 10.5)
        ax.set_ylim(-0.1, 1.15)
        ax.text(5.0, 0.0, f"Every level branches into {n} choices, giving {n}^{r} = {total} sequences.",
                ha="center", va="center", fontsize=9, fontweight="bold")
    else:
        fig, ax = plt.subplots(figsize=(8.5, 5.2))
        ks = list(range(min(max(r, 1), 20) + 1))
        ax.plot(ks, [log10(n ** k) for k in ks], marker="o", color=ORANGE, lw=2.0, label="With Repetition: n^k")
        no_rep = [k for k in ks if k <= n]
        if n > 0:
            ax.plot(no_rep, [log10(math.perm(n, k)) for k in no_rep], marker="s", color=BLUE, lw=2.0, linestyle="--",
                    label="Without Repetition: P(n, k)")
        ax.set_xlabel("Sequence Length k", **BOLD)
        ax.set_ylabel("log10( Count )", **BOLD)
        ax.set_title(f"Permutations with Repetition: n^k Growth (n = {n})", **TITLE)
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.5)
    return fig, "with repetition every slot keeps all n choices, so the count grows as n^r."


@chart
def plot_comb_with_repetition(n, r):
    total = combinatorics.combinations_with_repetition(n, r)
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    if n == 0 or r == 0:
        message(ax, f"Combinations with Repetition: Edge Case (n = {n}, r = {r})",
                f"n = {n}, r = {r}: result = {total}", GREEN)
        return fig, "with no types or no items to choose there is only the empty selection (or none at all)."

    ax.axis("off")
    ax.set_title(f"Stars & Bars: C({n} + {r} - 1, {r}) = C({n + r - 1}, {r}) = {total}", pad=12, **TITLE)
    # Three example ways to split r items among n types, each drawn as stars and bars,
    # e.g. counts [2, 1, 2] become "**|*|**". "spread" shares the items out as evenly as possible.
    spread = [r // n + (1 if i < r % n else 0) for i in range(n)]
    samples = [("Distributed Sample", spread), ("All in Type 1", [r] + [0] * (n - 1))]
    if n > 1:
        samples.append((f"All in Type {n}", [0] * (n - 1) + [r]))

    for y, (label, counts) in zip([0.72, 0.44, 0.16], samples):
        ax.text(0.02, y + 0.12, label + ":", fontsize=9.5, fontweight="bold", color="#1e3a8a")
        symbols = "|".join("*" * c for c in counts)
        x = 0.05
        for s in symbols[:25]:
            if s == "*":
                ax.add_patch(patches.Circle((x, y), 0.028, facecolor=GREEN, edgecolor="#14532d", zorder=4))
            else:
                ax.plot([x, x], [y - 0.05, y + 0.05], color=DARK, lw=2.5, zorder=5)
            x += 0.038
        if len(symbols) > 25:
            ax.text(x + 0.02, y, f"... +{len(symbols) - 25} symbols", fontsize=8.5, color="#64748b", va="center")
        breakdown = ", ".join(f"T{i + 1}:{c}" for i, c in enumerate(counts))
        ax.text(0.72, y, f"[{breakdown[:40]}{'...' if len(breakdown) > 40 else ''}]", fontsize=8.5, va="center", fontfamily="monospace")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    return fig, "stars are items and bars separate the types; placing r stars among n + r - 1 positions gives C(n + r - 1, r)."


@chart
def plot_multiset(text):
    total, freq = combinatorics.multiset_arrangements_count(text)
    chars = sorted(freq)
    fig, (ax_freq, ax_formula) = plt.subplots(1, 2, figsize=(10.0, 5.2), gridspec_kw={"width_ratios": [1.1, 1.2]})

    short = text[:20] + ("..." if len(text) > 20 else "")
    bars(ax_freq, chars, [freq[c] for c in chars], BLUE, "Unique Character", "Frequency Count",
         f"Frequencies in '{short}' (Length={len(text)})")
    for i, c in enumerate(chars):
        ax_freq.text(i, freq[c] + 0.1, str(freq[c]), ha="center", va="bottom", fontsize=9, fontweight="bold")

    labels = ["Total n!"] + [c + "!" for c in chars] + ["Result"]
    values = [log10(math.factorial(len(text)))] + [log10(math.factorial(freq[c])) for c in chars] + [log10(total)]
    bars(ax_formula, labels, values, [GRAY] + ["#cbd5e1"] * len(chars) + [ORANGE], ylabel="log10( Value )",
         title="Formula: n! / Product(ni!)")
    return fig, "identical letters are interchangeable, so dividing n! by each letter count's factorial removes the overcounting."


@chart
def plot_listing(mode, n=4, r=2, text=""):
    if mode == "perm":
        items, expected, ok = combinatorics.list_letter_permutations(n, r)
        title = f"Permutations P({n}, {r})"
    elif mode == "comb":
        items, expected, ok = combinatorics.list_letter_combinations(n, r)
        title = f"Combinations C({n}, {r})"
    elif mode == "multiset":
        items, expected, ok = combinatorics.list_multiset_permutations(text)
        title = f"Multiset Arrangements of '{text}'"
    else:
        raise ValueError(f"Invalid listing mode: {mode}")

    fig, (ax, ax_grid) = plt.subplots(1, 2, figsize=(10.5, 5.5), gridspec_kw={"width_ratios": [1.0, 1.8]})
    counts = [expected, len(items), len(set(items))]
    bars(ax, ["Formula", "List Items", "Unique Set"], counts, [BLUE, GREEN, ORANGE], ylabel="Count", width=0.55)
    ax.set_title(f"Verification: [{'MATCH' if ok else 'MISMATCH'}]", color="#15803d" if ok else "#b91c1c", **TITLE)
    for i, c in enumerate(counts):
        ax.text(i, c, str(c), ha="center", va="bottom", fontsize=9.5, fontweight="bold")

    # Draw up to 120 arrangements as small tiles in a grid.
    ax_grid.axis("off")
    ax_grid.set_title(title, pad=8, **TITLE)
    shown = items[:120]
    cols = 8 if len(shown) > 40 else 6
    rows = max(1, math.ceil(len(shown) / cols))
    tw, th = 0.90 / cols, 0.85 / rows
    for i, item in enumerate(shown):
        x = 0.05 + (i % cols) * (tw + 0.01)
        y = 0.90 - (i // cols + 1) * (th + 0.01)
        box(ax_grid, x, y, tw, th, "#f8fafc", GRAY, lw=0.8, pad=0.01)
        ax_grid.text(x + tw / 2, y + th / 2, "".join(item), ha="center", va="center", fontsize=7.5,
                     fontfamily="monospace", fontweight="bold")
    if len(items) > len(shown):
        ax_grid.text(0.5, 0.02, f"+ {len(items) - len(shown)} more items...", ha="center", fontsize=9, style="italic", color=MUTED)
    return fig, "every arrangement is stored as a tuple; putting them in a set proves they are all unique and match the formula."


@chart
def plot_binomial_identities(n, r):
    rep = combinatorics.verify_binomial_identities(n, r)
    fig, (ax_sym, ax_pascal, ax_sum) = plt.subplots(3, 1, figsize=(9.5, 8.5))

    # Highlight both C(n, r) and its mirror C(n, n - r) to show the symmetry.
    ks = sorted(set(sample_k(n, r)) | {n - r})
    bars(ax_sym, ks, [log10(math.comb(n, k)) for k in ks], [ORANGE if k in (r, n - r) else GREEN for k in ks], ylabel="log10( C )")
    ax_sym.set_title(f"1. Symmetry: C({n}, {r}) = C({n}, {n - r}) [VERIFIED]", color="#15803d", **TITLE)

    if rep["pascal_applicable"]:
        parts = [math.comb(n - 1, r - 1), math.comb(n - 1, r), rep["c_nr"]]
        bars(ax_pascal, [f"C({n - 1},{r - 1})", f"C({n - 1},{r})", f"Sum = C({n},{r})"], [log10(v) for v in parts],
             [GRAY, GRAY, ORANGE], ylabel="log10( C )", width=0.5)
        ax_pascal.set_title("2. Pascal's Rule: C(n-1, r-1) + C(n-1, r) = C(n, r) [VERIFIED]", color="#15803d", **TITLE)
    else:
        ax_pascal.axis("off")
        ax_pascal.text(0.5, 0.5, f"2. Pascal's Rule: not applicable for boundary r = {r} (needs 1 <= r <= n-1)",
                       ha="center", va="center", fontsize=9.5, style="italic", color=MUTED)

    bars(ax_sum, [f"Sum of C({n}, k)", f"2^{n}"], [log10(rep["row_sum_value"]), log10(rep["power_of_two"])], [GREEN, BLUE],
         ylabel="log10( Sum )", width=0.45)
    ax_sum.set_title(f"3. Row Sum: row {n} adds up to 2^{n} [VERIFIED]", color="#15803d", **TITLE)
    return fig, "symmetry mirrors the row, Pascal's rule builds each entry by addition, and every row sums to 2^n."


@chart
def plot_pascal_triangle(num_rows):
    triangle = combinatorics.generate_pascal_triangle(num_rows)
    fig, (ax_tri, ax_par) = plt.subplots(1, 2, figsize=(11.0, 5.8), gridspec_kw={"width_ratios": [1.4, 1.0]})
    ax_tri.set_title(f"Pascal's Triangle (Rows 0 to {num_rows - 1})", pad=10, **TITLE)
    ax_par.set_title("Odd / Even Pattern (Sierpinski Triangle)", pad=10, **TITLE)

    # Both panels use the same cell positions: the left shows the numbers,
    # the right fills odd cells blue, which reveals the Sierpinski triangle pattern.
    for i, row in enumerate(triangle):
        y = -i * 1.05
        ax_tri.text(num_rows * 0.55, y, f"Sum = 2^{i} = {2 ** i}", fontsize=7.5, color=MUTED, va="center")
        for j, value in enumerate(row):
            x = (j - i / 2) * 1.15
            box(ax_tri, x - 0.425, y - 0.35, 0.85, 0.7, "#eff6ff", BLUE, lw=1.2)
            ax_tri.text(x, y, str(value), ha="center", va="center", fontsize=8 if num_rows <= 8 else 6.5, fontweight="bold")
            odd = value % 2 == 1
            box(ax_par, x - 0.425, y - 0.35, 0.85, 0.7, BLUE if odd else "white", BLUE if odd else "#cbd5e1", lw=0.8)

    for ax, right in ((ax_tri, 0.95), (ax_par, 0.65)):
        ax.axis("off")
        ax.set_xlim(-num_rows * 0.65, num_rows * right)
        ax.set_ylim(-num_rows * 1.05 - 0.5, 0.8)
    ax_par.text(0, -num_rows * 1.05 - 0.2, "Blue = Odd | White = Even", ha="center", va="center", fontsize=8, fontweight="bold")
    return fig, "each cell is the sum of the two above it; colouring odd cells reveals the Sierpinski triangle."


@chart
def plot_recurrence(rec_type, terms, label="Recurrence Sequence"):
    idx = list(range(len(terms)))
    if rec_type == "fibonacci" and len(terms) >= 3:
        fig, (ax, ax_ratio) = plt.subplots(2, 1, figsize=(9.0, 7.0), gridspec_kw={"height_ratios": [1.4, 1.0]})
        logs = [log10(t) for t in terms]
        ax.plot(idx, logs, marker="o", color=BLUE, lw=2.0, markersize=5)
        ax.set_ylabel("log10( F(n) )", **BOLD)
        ax.set_title("Fibonacci Sequence: F(n) = F(n-1) + F(n-2)", **TITLE)
        for i in range(min(5, len(terms))):
            ax.text(i, logs[i] + 0.1, f"F({i})={terms[i]}", fontsize=7.5, color="#1e3a8a", ha="center")
        # F(n+1) / F(n) approaches the golden ratio (1 + sqrt(5)) / 2.
        ratio_idx = [i for i in range(1, len(terms) - 1) if terms[i] > 0]
        ax_ratio.plot(ratio_idx, [terms[i + 1] / terms[i] for i in ratio_idx], marker="s", color=ORANGE, lw=1.8, label="F(n+1) / F(n)")
        ax_ratio.axhline((1 + math.sqrt(5)) / 2, color="#16a34a", linestyle="--", lw=1.5, label="Golden Ratio ~ 1.61803")
        ax_ratio.set_xlabel("Term Index n", **BOLD)
        ax_ratio.set_title("Convergence to the Golden Ratio", **TITLE)
        ax_ratio.set_ylim(1.0, 2.2)
        ax_ratio.legend(loc="upper right", fontsize=8.5)
        ax_ratio.grid(True, linestyle="--", alpha=0.5)
    else:
        fig, ax = plt.subplots(figsize=(8.5, 5.2))
        # Switch to a log scale for big values, but only if none are negative (log needs > 0).
        use_log = max(abs(t) for t in terms) > 10 ** 6 and min(terms) >= 0
        values = [log10(t) for t in terms] if use_log else terms
        ax.plot(idx, values, marker="o", color=BLUE, lw=2.0, markersize=5)
        ax.set_xlabel("Term Index n", **BOLD)
        ax.set_ylabel("log10( a(n) )" if use_log else "a(n)", **BOLD)
        ax.set_title(f"Recurrence Sequence: {label}", **TITLE)
        for i in range(min(4, len(terms))):
            ax.text(i, values[i], f" a({i})={terms[i]}", fontsize=7.5, color="#1e3a8a", va="bottom")
    ax.grid(True, linestyle="--", alpha=0.5)
    return fig, "each term is built from the previous ones; ratios of linear recurrences settle towards a fixed root."


@chart
def plot_binomial_expansion(n, a, b):
    terms = combinatorics.binomial_expansion_terms(n, a, b)
    fig, (ax, ax_pascal) = plt.subplots(1, 2, figsize=(11.0, 5.2), gridspec_kw={"width_ratios": [1.4, 1.0]})

    # Coefficients are converted to float only for the bar heights. The largest allowed
    # input, (10x + 10y)^20, has coefficients around 1e25, which a float handles easily.
    coeffs = [c for c, _, _ in terms]
    labels = [combinatorics.term_variables(xp, yp) or "1" for _, xp, yp in terms]
    bars(ax, labels, [float(c) for c in coeffs], [BLUE if c >= 0 else RED for c in coeffs], "Term", "Coefficient",
         "Expansion Coefficients: " + combinatorics.binomial_label(n, a, b))
    ax.axhline(0, color="#64748b", lw=1.0)
    ax.tick_params(axis="x", rotation=30)
    biggest = float(max(abs(c) for c in coeffs)) or 1.0
    for i, c in enumerate(coeffs):
        text = f"{c:.2e}" if len(str(abs(c))) > 7 else str(c)
        ax.text(i, c + (0.03 if c >= 0 else -0.03) * biggest, text, ha="center", va="bottom" if c >= 0 else "top",
                fontsize=7 if len(coeffs) > 10 else 8, fontweight="bold")

    ks = list(range(n + 1))
    bars(ax_pascal, ks, [math.comb(n, k) for k in ks], GREEN, "k", f"C({n}, k)", f"Pascal Row {n}")
    return fig, "the binomial theorem scales each Pascal number C(n, k) by a^(n-k) * b^k."


@chart
def plot_derangements(n):
    values = combinatorics.derangements_list(n)
    ratio = combinatorics.derangements_report(n)["ratio"]
    fig, (ax, ax_ratio) = plt.subplots(1, 2, figsize=(11.0, 5.2), gridspec_kw={"width_ratios": [1.2, 1.0]})

    ks = sample_k(n, limit=20)
    pos = list(range(len(ks)))
    w = 0.38
    ax.bar([p + w / 2 for p in pos], [log10(math.factorial(k)) for k in ks], width=w, label="All Permutations k!", color=GRAY, edgecolor=DARK, linewidth=0.5)
    ax.bar([p - w / 2 for p in pos], [log10(values[k]) for k in ks], width=w, label="Derangements D(k)", color=ORANGE, edgecolor=DARK, linewidth=0.5)
    ax.set_xticks(pos)
    ax.set_xticklabels([str(k) for k in ks])
    ax.set_xlabel("Size k", **BOLD)
    ax.set_ylabel("log10( Count )", **BOLD)
    ax.set_title(f"Derangements D(k) vs k! (n = {n})", **TITLE)
    ax.legend(loc="upper left", fontsize=8.5)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    # D(k) / k! reaches 1/e within a few steps, so the ratio panel only needs k up to 15.
    small = combinatorics.derangements_list(15)
    ratio_k = list(range(1, min(max(n, 7), 15) + 1))
    ax_ratio.plot(ratio_k, [small[k] / math.factorial(k) for k in ratio_k], marker="o", color=BLUE, lw=2.0, label="D(k) / k!")
    ax_ratio.axhline(1 / math.e, color=RED, linestyle="--", lw=1.8, label=f"Limit 1/e ~ {1 / math.e:.4f}")
    ax_ratio.set_xlabel("Size k", **BOLD)
    ax_ratio.set_ylabel("D(k) / k!", **BOLD)
    ax_ratio.set_title(f"Convergence to 1/e (at n = {n}: {ratio:.5f})", **TITLE)
    ax_ratio.set_ylim(0, 0.6)
    ax_ratio.legend(loc="upper right", fontsize=8.5)
    ax_ratio.grid(True, linestyle="--", alpha=0.5)
    return fig, "derangements are permutations with no item in its own place; about 1/e (36.8%) of all permutations are derangements."


@chart
def plot_circular_permutations(n, r=None, allow_reflections=False):
    r = n if r is None else r
    count = combinatorics.circular_permutations(n, r, allow_reflections)
    fig, ax = plt.subplots(figsize=(8.5, 6.0))
    if r == 0:
        message(ax, f"Circular Permutations: Edge Case (n={n}, r=0)", "Exactly 1 empty circular arrangement [Result = 1]")
        return fig, "with nothing to place there is exactly one (empty) arrangement."

    # Draw up to 8 labelled items evenly around a circle, starting at the top.
    ax.axis("off")
    shown = min(r, 8)
    ax.add_patch(patches.Circle((0.5, 0.5), 0.32, fill=False, edgecolor="#64748b", lw=2.0, linestyle="--"))
    for i in range(shown):
        angle = 2 * math.pi * i / shown + math.pi / 2
        x, y = 0.5 + 0.32 * math.cos(angle), 0.5 + 0.32 * math.sin(angle)
        ax.add_patch(patches.Circle((x, y), 0.045, facecolor="#eff6ff", edgecolor=BLUE, lw=1.5, zorder=5))
        ax.text(x, y, combinatorics.LETTERS[i], ha="center", va="center", fontsize=10, fontweight="bold", zorder=6)
    divisor = f"{r} rotations" + (" x 2 reflections" if allow_reflections and r >= 3 else "")
    ax.text(0.5, 0.54, f"Circular count = {count}", ha="center", va="center", fontsize=11, fontweight="bold", color="#1e3a8a")
    ax.text(0.5, 0.44, f"P({n}, {r}) divided by {divisor}", ha="center", va="center", fontsize=9, color=MUTED)
    ax.set_title(f"Circular Permutations of {r} out of {n} items = {count}", pad=10, **TITLE)
    return fig, f"rotating a circle of {r} items gives the same arrangement, so the linear count is divided by {r}."


# Example inputs for the CLI's "Visual gallery" option, which draws one chart of each type.
DEMO_PLOTS = [
    ("Factorial (n=6)", plot_factorial, (6,)),
    ("Permutations P(6, 3)", plot_permutations, (6, 3)),
    ("Combinations C(6, 3)", plot_combinations, (6, 3)),
    ("Comparison P vs C (6, 3)", plot_comparison, (6, 3)),
    ("Permutations with Repetition (3^4)", plot_perm_with_repetition, (3, 4)),
    ("Combinations with Repetition (n=4, r=3)", plot_comb_with_repetition, (4, 3)),
    ("Multiset Arrangements ('MISSISSIPPI')", plot_multiset, ("MISSISSIPPI",)),
    ("Listing P(4, 2)", plot_listing, ("perm", 4, 2)),
    ("Binomial Identities (n=6, r=3)", plot_binomial_identities, (6, 3)),
    ("Pascal's Triangle (rows=8)", plot_pascal_triangle, (8,)),
    ("Fibonacci (10 terms)", plot_recurrence, ("fibonacci", recurrence.fibonacci_sequence(10), "Fibonacci")),
    ("Binomial Expansion ((x+y)^5)", plot_binomial_expansion, (5, 1, 1)),
    ("Derangements D(5)", plot_derangements, (5,)),
    ("Circular Permutations (5, 3)", plot_circular_permutations, (5, 3)),
]


def generate_all_demo_plots():
    if not MATPLOTLIB_AVAILABLE:
        return []
    return [(name, func(*args)) for name, func, args in DEMO_PLOTS]
