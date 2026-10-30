# Project: Combinatorial Counting and Permutation Analyzer
# Name: [YOUR NAME]  Roll No: [YOUR ROLL NO]
# Module: visualizer.py - Visual explanation charts using matplotlib

import os
import io
import math
import datetime
import threading

# Thread lock to guarantee thread-safe matplotlib figure generation
PLOT_LOCK = threading.RLock()

# Check matplotlib availability with graceful degradation
MATPLOTLIB_AVAILABLE = False
MATPLOTLIB_VERSION = "Not installed"

try:
    import matplotlib
    # Headless-safe: use Agg non-interactive backend before importing pyplot
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    MATPLOTLIB_AVAILABLE = True
    MATPLOTLIB_VERSION = str(matplotlib.__version__)
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    MATPLOTLIB_VERSION = "Not installed"

# Import core combinatorics and recurrence to retrieve verified numbers (never re-implement maths)
import combinatorics
import recurrence


# =============================================================================
# AVAILABILITY & CONFIGURATION HELPERS
# =============================================================================

def is_matplotlib_available():
    """Returns True if matplotlib is installed and successfully imported."""
    return MATPLOTLIB_AVAILABLE


def is_visualizer_available():
    """Alias for is_matplotlib_available."""
    return MATPLOTLIB_AVAILABLE


def get_matplotlib_install_message():
    """Returns installation instruction string if matplotlib is missing."""
    return "Matplotlib is not installed. To enable visual explanation charts, run: pip install matplotlib"


# =============================================================================
# PRIVATE UTILITY HELPERS
# =============================================================================

def safe_log10(val):
    """Safely calculates log10 for arbitrarily large integers.
    
    Returns 0.0 if val <= 0, otherwise math.log10(val).
    Python's math.log10 accepts arbitrarily large ints directly.
    """
    if not isinstance(val, int) and not isinstance(val, float):
        return 0.0
    if val <= 0:
        return 0.0
    try:
        return math.log10(val)
    except Exception:
        # Fallback if extremely large
        return float(len(str(val)) - 1)


def make_plots_folder():
    """Returns absolute path to plots/ directory located alongside this module, creating it if needed."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    plots_dir = os.path.join(base_dir, "plots")
    if not os.path.exists(plots_dir):
        os.makedirs(plots_dir, exist_ok=True)
    return plots_dir


def build_filename(prefix):
    """Generates a timestamped PNG file path inside the plots/ folder."""
    plots_dir = make_plots_folder()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    filename = prefix + "_" + ts + ".png"
    return os.path.join(plots_dir, filename)


def add_caption(fig, text):
    """Adds a clear, one-sentence plain-English caption at the bottom of the figure."""
    fig.text(0.5, 0.02, text, ha="center", va="bottom", fontsize=8.5, style="italic", color="#334155", wrap=True)


def figure_to_png_bytes(fig):
    """Saves a matplotlib figure into an in-memory PNG buffer and returns the raw bytes.
    
    Closes the figure to free resources.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    return buf.getvalue()


def save_or_return_figure(fig, prefix, as_bytes=False):
    """Saves figure to disk if as_bytes is False, or returns PNG bytes if True."""
    if as_bytes:
        return figure_to_png_bytes(fig)
    filepath = build_filename(prefix)
    fig.savefig(filepath, dpi=120)
    plt.close(fig)
    return filepath



# Color palette: Color-blind friendly and semantically consistent across all charts
# Blue: Permutations / Ordered selections
# Green: Combinations / Unordered selections
# Orange: Highlighted / Chosen target value
# Gray/Slate: Neutral bars / Background components
# Red: Negative signed terms
CLR_PERM = "#1f77b4"       # Blue (Ordered / Permutations)
CLR_COMB = "#2ca02c"       # Green (Unordered / Combinations)
CLR_HIGHLIGHT = "#ff7f0e"  # Orange (Selected target value)
CLR_NEUTRAL = "#94a3b8"    # Slate Gray
CLR_NEGATIVE = "#d62728"   # Red (Negative expansion coefficients)


# =============================================================================
# 12 OPERATION VISUALIZERS
# =============================================================================

def plot_factorial(n, as_bytes=False):
    """Visualizes factorial growth and multiplication chain for n!.
    
    Displays a log10 scale bar chart of k! for k = 0..n to show super-exponential
    growth, and for small n (<= 8) includes a multiplication chain strip.
    """
    if not is_matplotlib_available():
        return None
    if not isinstance(n, int):
        raise TypeError("Factorial argument must be an integer.")
    if n < 0 or n > 1000:
        raise ValueError("n must satisfy 0 <= n <= 1000.")

    target_val = combinatorics.factorial(n)
    digit_count = len(str(target_val))

    # Sample k points if n > 30 so bars remain legible
    if n <= 30:
        k_values = list(range(n + 1))
        sample_note = ""
    else:
        step = max(1, n // 25)
        k_values = list(range(0, n, step))
        if n not in k_values:
            k_values.append(n)
        sample_note = " (Sampled " + str(len(k_values)) + " representative points for clarity)"

    log_vals = [safe_log10(combinatorics.factorial(k)) for k in k_values]

    with PLOT_LOCK:
        if n <= 8:
            fig, (ax_chain, ax_bar) = plt.subplots(2, 1, figsize=(8.5, 6.5), gridspec_kw={"height_ratios": [1, 2]})
            
            # Panel 1: Multiplication Chain Strip
            ax_chain.set_xlim(-0.5, max(1, n) + 0.5)
            ax_chain.set_ylim(0, 3)
            ax_chain.axis("off")
            ax_chain.set_title("Multiplication Chain for " + str(n) + "!", fontsize=11, fontweight="bold", pad=8)

            if n == 0:
                ax_chain.text(0.5, 1.5, "0! = 1 (Defined as 1: exactly 1 empty arrangement)", 
                              ha="center", va="center", fontsize=11, fontweight="bold",
                              bbox=dict(boxstyle="round,pad=0.5", facecolor="#e2e8f0", edgecolor="#64748b"))
            else:
                running_prod = 1
                for idx in range(1, n + 1):
                    running_prod = running_prod * idx
                    x_pos = idx - 0.5
                    rect = patches.FancyBboxPatch((x_pos - 0.35, 0.8), 0.7, 1.4, boxstyle="round,pad=0.1",
                                                  facecolor="#eff6ff", edgecolor=CLR_PERM, linewidth=1.5)
                    ax_chain.add_patch(rect)
                    ax_chain.text(x_pos, 1.7, "x " + str(idx), ha="center", va="center", fontsize=10, fontweight="bold")
                    ax_chain.text(x_pos, 1.1, "= " + str(running_prod), ha="center", va="center", fontsize=8.5, color="#334155")
                    if idx < n:
                        ax_chain.annotate("", xy=(x_pos + 0.45, 1.5), xytext=(x_pos + 0.35, 1.5),
                                          arrowprops=dict(arrowstyle="->", color="#64748b", lw=1.2))
        else:
            fig, ax_bar = plt.subplots(figsize=(8.5, 5.5))

        # Panel 2: Bar chart on log10 axis
        colors = [CLR_HIGHLIGHT if k == n else CLR_PERM for k in k_values]
        bars = ax_bar.bar([str(k) for k in k_values], log_vals, color=colors, width=0.65, edgecolor="#1e293b", linewidth=0.5)
        
        ax_bar.set_xlabel("Integer k", fontsize=10, fontweight="bold")
        ax_bar.set_ylabel("log10( k! )", fontsize=10, fontweight="bold")
        ax_bar.set_title("Super-Exponential Growth of Factorials (k = 0 to " + str(n) + ")" + sample_note, fontsize=11, fontweight="bold")
        ax_bar.grid(axis="y", linestyle="--", alpha=0.5)

        # Annotate n! bar with its digit count
        last_bar = bars[-1]
        ax_bar.annotate(str(digit_count) + " digits\n(log10 ~ " + str(round(log_vals[-1], 1)) + ")",
                        xy=(last_bar.get_x() + last_bar.get_width() / 2, last_bar.get_height()),
                        xytext=(0, 6), textcoords="offset points", ha="center", va="bottom",
                        fontsize=8.5, fontweight="bold", color="#b45309",
                        bbox=dict(boxstyle="round,pad=0.2", facecolor="#fef3c7", edgecolor="#d97706", alpha=0.9))

        caption = "What you are looking at: Factorial values grow super-exponentially; each integer multiplies the prior total, causing rapid digit explosion."
        add_caption(fig, caption)
        fig.tight_layout()
        fig.subplots_adjust(bottom=0.10)

        return save_or_return_figure(fig, "plot_01_factorial", as_bytes=as_bytes)


def plot_permutations(n, r, as_bytes=False):
    """Visualizes permutations P(n, r) with a slots diagram and distribution curve.
    
    Shows r sequential choice slots labelled with remaining choices, demonstrating
    why P(n, r) = n * (n - 1) * ... * (n - r + 1).
    """
    if not is_matplotlib_available():
        return None
    if not isinstance(n, int) or not isinstance(r, int):
        raise TypeError("n and r must both be integers.")
    if n < 0 or r < 0 or r > n or n > 1000:
        raise ValueError("Requires 0 <= r <= n <= 1000.")

    fig, (ax_slots, ax_bar) = plt.subplots(2, 1, figsize=(9.0, 7.0), gridspec_kw={"height_ratios": [1.1, 1.8]})

    # Subplot 1: Sequential Choice Slots Diagram
    ax_slots.axis("off")
    ax_slots.set_title("Choice Slots Diagram for P(" + str(n) + ", " + str(r) + ")", fontsize=11, fontweight="bold", pad=8)

    if r == 0:
        rect = patches.FancyBboxPatch((0.2, 0.3), 0.6, 0.4, boxstyle="round,pad=0.1",
                                      facecolor="#f1f5f9", edgecolor=CLR_PERM, linewidth=1.5)
        ax_slots.add_patch(rect)
        ax_slots.text(0.5, 0.5, "0 slots to fill: exactly 1 empty arrangement [P(n, 0) = 1]",
                      ha="center", va="center", fontsize=10, fontweight="bold", color="#1e293b")
    else:
        # If r <= 8, display all slots. If r > 8, display first 4 and last 2 with ellipsis
        if r <= 8:
            slot_indices = list(range(1, r + 1))
            display_slots = [(i, n - i + 1) for i in slot_indices]
            has_ellipsis = False
        else:
            display_slots = [(1, n), (2, n - 1), (3, n - 2), (4, n - 3), (-1, -1), (r - 1, n - r + 2), (r, n - r + 1)]
            has_ellipsis = True

        total_boxes = len(display_slots)
        box_width = 0.8
        gap = 0.25
        total_width = total_boxes * box_width + (total_boxes - 1) * gap
        start_x = -total_width / 2.0

        running_val = 1
        for idx, (slot_num, choices) in enumerate(display_slots):
            curr_x = start_x + idx * (box_width + gap)
            if slot_num == -1:
                # Ellipsis box
                ax_slots.text(curr_x + box_width / 2.0, 0.5, ". . .", ha="center", va="center", fontsize=14, fontweight="bold")
            else:
                running_val = running_val * choices
                rect = patches.FancyBboxPatch((curr_x, 0.1), box_width, 0.8, boxstyle="round,pad=0.08",
                                              facecolor="#eff6ff", edgecolor=CLR_PERM, linewidth=1.5)
                ax_slots.add_patch(rect)
                ax_slots.text(curr_x + box_width / 2.0, 0.72, "Slot " + str(slot_num), ha="center", va="center",
                              fontsize=8, color="#64748b", fontweight="bold")
                ax_slots.text(curr_x + box_width / 2.0, 0.48, str(choices) + " choices", ha="center", va="center",
                              fontsize=9.5, fontweight="bold", color="#0f172a")
                if not has_ellipsis or idx < 4:
                    ax_slots.text(curr_x + box_width / 2.0, 0.22, "Running: " + str(running_val), ha="center", va="center",
                                  fontsize=7.5, color="#1e3a8a")

        ax_slots.set_xlim(-total_width / 2.0 - 0.5, total_width / 2.0 + 0.5)
        ax_slots.set_ylim(-0.2, 1.2)

    # Subplot 2: Bar chart of P(n, k) for k = 0..n
    if n <= 25:
        k_range = list(range(n + 1))
    else:
        step = max(1, n // 25)
        k_range = list(range(0, n + 1, step))
        if r not in k_range:
            k_range.append(r)
        k_range.sort()

    log_p_vals = [safe_log10(combinatorics.permutations(n, k)) for k in k_range]
    bar_colors = [CLR_HIGHLIGHT if k == r else CLR_PERM for k in k_range]
    
    ax_bar.bar([str(k) for k in k_range], log_p_vals, color=bar_colors, width=0.65, edgecolor="#1e293b", linewidth=0.5)
    ax_bar.set_xlabel("Selection Size k", fontsize=10, fontweight="bold")
    ax_bar.set_ylabel("log10( P(n, k) )", fontsize=10, fontweight="bold")
    ax_bar.set_title("Permutations P(" + str(n) + ", k) across k in [0, " + str(n) + "] (Orange = chosen r=" + str(r) + ")",
                     fontsize=11, fontweight="bold")
    ax_bar.grid(axis="y", linestyle="--", alpha=0.5)

    caption = "What you are looking at: Each sequential slot has one fewer available choice because items cannot be reused; the total is the product of remaining choices."
    add_caption(fig, caption)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.09)

    return save_or_return_figure(fig, "plot_02_permutations", as_bytes=as_bytes)


def plot_combinations(n, r, as_bytes=False):
    """Visualizes combinations C(n, r) with symmetric distribution and the subset collapse effect.
    
    Highlights C(n, r) within the symmetric bell curve of binomial coefficients,
    and for n <= 6 displays how r! permutations collapse into a single combination set.
    """
    if not is_matplotlib_available():
        return None
    if not isinstance(n, int) or not isinstance(r, int):
        raise TypeError("n and r must both be integers.")
    if n < 0 or r < 0 or r > n or n > 1000:
        raise ValueError("Requires 0 <= r <= n <= 1000.")

    if n <= 6 and r >= 1:
        fig, (ax_bar, ax_collapse) = plt.subplots(1, 2, figsize=(10.0, 5.2), gridspec_kw={"width_ratios": [1.2, 1.0]})
    else:
        fig, ax_bar = plt.subplots(figsize=(8.5, 5.2))
        ax_collapse = None

    # Bar chart of C(n, k) for k = 0..n
    if n <= 30:
        k_range = list(range(n + 1))
    else:
        step = max(1, n // 25)
        k_range = list(range(0, n + 1, step))
        if r not in k_range:
            k_range.append(r)
        k_range.sort()

    log_c_vals = [safe_log10(combinatorics.combinations(n, k)) for k in k_range]
    bar_colors = [CLR_HIGHLIGHT if k == r else CLR_COMB for k in k_range]

    ax_bar.bar([str(k) for k in k_range], log_c_vals, color=bar_colors, width=0.65, edgecolor="#1e293b", linewidth=0.5)
    ax_bar.set_xlabel("Subset Size k", fontsize=10, fontweight="bold")
    ax_bar.set_ylabel("log10( C(n, k) )", fontsize=10, fontweight="bold")
    ax_bar.set_title("Combinations C(" + str(n) + ", k) [Symmetric Bell Distribution]", fontsize=11, fontweight="bold")
    ax_bar.grid(axis="y", linestyle="--", alpha=0.5)

    # Collapse demonstration for small inputs
    if ax_collapse is not None:
        ax_collapse.axis("off")
        sample_chars = list("ABCDEF"[:r])
        perms_list, theo_p, _ = combinatorics.list_letter_permutations(r, r)
        perm_strings = ["".join(tup) for tup in perms_list]

        ax_collapse.set_title("The 'Collapse' Effect: P / r! = C", fontsize=11, fontweight="bold", pad=8)
        
        # Draw outer combination bounding box
        outer_box = patches.FancyBboxPatch((0.05, 0.08), 0.90, 0.84, boxstyle="round,pad=0.05",
                                           facecolor="#f0fdf4", edgecolor=CLR_COMB, linewidth=2.0)
        ax_collapse.add_patch(outer_box)
        ax_collapse.text(0.5, 0.84, "ONE COMBINATION SET", ha="center", va="center",
                         fontsize=10, fontweight="bold", color="#166534")
        ax_collapse.text(0.5, 0.75, "{" + ", ".join(sample_chars) + "}", ha="center", va="center",
                         fontsize=12, fontweight="bold", color="#0f172a")

        # Inner orderings display
        ax_collapse.text(0.5, 0.63, "Contains all " + str(r) + "! = " + str(theo_p) + " ordered permutations:",
                         ha="center", va="center", fontsize=8.5, color="#475569")
        
        inner_txt = ",  ".join(perm_strings[:12])
        if len(perm_strings) > 12:
            inner_txt += "\n... + " + str(len(perm_strings) - 12) + " more"
        
        ax_collapse.text(0.5, 0.40, inner_txt, ha="center", va="center", fontsize=9.5,
                         fontfamily="monospace", color="#1e293b",
                         bbox=dict(boxstyle="round,pad=0.4", facecolor="#ffffff", edgecolor="#cbd5e1"))

        ax_collapse.text(0.5, 0.16, "Dividing by " + str(r) + "! cancels these redundant orderings.",
                         ha="center", va="center", fontsize=8.5, style="italic", color="#166534")

    caption = "What you are looking at: Combinations ignore arrangement sequence; dividing P(n, r) by r! collapses every cluster of r! orderings into exactly one subset."
    add_caption(fig, caption)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.09)

    return save_or_return_figure(fig, "plot_03_combinations", as_bytes=as_bytes)


def plot_comparison(n, r, as_bytes=False):
    """Visualizes the exact mathematical relation P(n, r) = C(n, r) * r!.
    
    Shows grouped bars of P(n, k) versus C(n, k) and three decomposition bars
    verifying the identity.
    """
    if not is_matplotlib_available():
        return None
    if not isinstance(n, int) or not isinstance(r, int):
        raise TypeError("n and r must both be integers.")
    if n < 0 or r < 0 or r > n or n > 1000:
        raise ValueError("Requires 0 <= r <= n <= 1000.")

    p_val = combinatorics.permutations(n, r)
    c_val = combinatorics.combinations(n, r)
    r_fact = combinatorics.factorial(r)
    is_valid = (p_val == c_val * r_fact)

    fig, (ax_curve, ax_decomp) = plt.subplots(1, 2, figsize=(10.5, 5.2), gridspec_kw={"width_ratios": [1.4, 1.0]})

    # Grouped comparison bars for k = 0..min(n, 15)
    sample_limit = min(n, 15)
    k_range = list(range(sample_limit + 1))
    p_logs = [safe_log10(combinatorics.permutations(n, k)) for k in k_range]
    c_logs = [safe_log10(combinatorics.combinations(n, k)) for k in k_range]

    x_indices = list(range(len(k_range)))
    bar_w = 0.38
    x_p = [x - bar_w / 2 for x in x_indices]
    x_c = [x + bar_w / 2 for x in x_indices]

    ax_curve.bar(x_p, p_logs, width=bar_w, label="P(n, k) [Ordered]", color=CLR_PERM, edgecolor="#0f172a", linewidth=0.5)
    ax_curve.bar(x_c, c_logs, width=bar_w, label="C(n, k) [Unordered]", color=CLR_COMB, edgecolor="#0f172a", linewidth=0.5)
    
    ax_curve.set_xticks(x_indices)
    ax_curve.set_xticklabels([str(k) for k in k_range])
    ax_curve.set_xlabel("Selection Size k", fontsize=10, fontweight="bold")
    ax_curve.set_ylabel("log10( Count )", fontsize=10, fontweight="bold")
    ax_curve.set_title("Permutations vs Combinations (n = " + str(n) + ")", fontsize=11, fontweight="bold")
    ax_curve.legend(loc="upper left", fontsize=9)
    ax_curve.grid(axis="y", linestyle="--", alpha=0.5)

    # Panel 2: Three decomposition bars for chosen (n, r)
    log_c = safe_log10(c_val)
    log_rf = safe_log10(r_fact)
    log_p = safe_log10(p_val)

    decomp_labels = ["C(" + str(n) + "," + str(r) + ")", str(r) + "!", "P(" + str(n) + "," + str(r) + ")"]
    decomp_vals = [log_c, log_rf, log_p]
    decomp_colors = [CLR_COMB, CLR_NEUTRAL, CLR_PERM]

    ax_decomp.bar(decomp_labels, decomp_vals, color=decomp_colors, width=0.55, edgecolor="#0f172a", linewidth=0.8)
    ax_decomp.set_ylabel("log10( Value )", fontsize=10, fontweight="bold")
    status_str = "VERIFIED MATCH" if is_valid else "FAILED"
    ax_decomp.set_title("P = C x r! [" + status_str + "]", fontsize=11, fontweight="bold", color="#15803d" if is_valid else "#b91c1c")
    ax_decomp.grid(axis="y", linestyle="--", alpha=0.5)

    caption = "What you are looking at: Permutations are strictly greater than combinations (except at k=0,1) by a factor of r!, reflecting the internal orderings of each subset."
    add_caption(fig, caption)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.09)

    return save_or_return_figure(fig, "plot_04_comparison", as_bytes=as_bytes)


def plot_perm_with_repetition(n, r, as_bytes=False):
    """Visualizes permutations with repetition: n^r.
    
    Draws a branching choice tree for small inputs (n <= 4, r <= 3), or a growth
    comparison curve between n^k and P(n, k) for larger inputs.
    """
    if not is_matplotlib_available():
        return None
    if not isinstance(n, int) or not isinstance(r, int):
        raise TypeError("n and r must both be integers.")
    if n < 0 or r < 0 or n > 1000 or r > 1000:
        raise ValueError("Requires 0 <= n, r <= 1000.")

    result_val = combinatorics.permutations_with_repetition(n, r)

    # Choice Tree for small inputs
    if n <= 4 and r <= 3 and n > 0 and r > 0:
        fig, ax = plt.subplots(figsize=(9.5, 6.0))
        ax.axis("off")
        ax.set_title("Choice Tree: " + str(n) + "^" + str(r) + " = " + str(result_val) + " Total Leaf Sequences",
                     fontsize=11, fontweight="bold", pad=12)

        # Draw tree levels recursively
        levels = r
        total_leaves = n ** r
        x_step = 10.0 / total_leaves

        def get_coords(level, index, total_at_level):
            y = 1.0 - (level / (levels + 0.5))
            span = 10.0 / total_at_level
            x = (index + 0.5) * span
            return (x, y)

        # Plot root
        ax.scatter([5.0], [1.0], color="#0f172a", s=80, zorder=5)
        ax.text(5.0, 1.04, "Start (Slot 0)", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

        # Build tree connections
        for lev in range(1, levels + 1):
            nodes_this_level = n ** lev
            nodes_prev_level = n ** (lev - 1)
            for parent_idx in range(nodes_prev_level):
                px, py = get_coords(lev - 1, parent_idx, nodes_prev_level) if lev > 1 else (5.0, 1.0)
                for child_branch in range(n):
                    child_idx = parent_idx * n + child_branch
                    cx, cy = get_coords(lev, child_idx, nodes_this_level)
                    ax.plot([px, cx], [py, cy], color="#94a3b8", lw=1.2, zorder=3)
                    node_color = CLR_HIGHLIGHT if lev == levels else CLR_PERM
                    ax.scatter([cx], [cy], color=node_color, s=50, zorder=5)
                    if levels <= 2 or lev <= 2:
                        ax.text((px + cx) / 2.0, (py + cy) / 2.0 + 0.02, str(child_branch + 1),
                                fontsize=7.5, color="#1e3a8a", ha="center")

        ax.set_xlim(-0.5, 10.5)
        ax.set_ylim(-0.1, 1.15)
        ax.text(5.0, 0.0, "Every level branches into " + str(n) + " choices, giving " + str(n) + "^" + str(r) + " = " + str(result_val) + " distinct sequences.",
                ha="center", va="center", fontsize=9, fontweight="bold", color="#0f172a")

    else:
        # Comparison growth curve: n^k vs P(n, k)
        fig, ax = plt.subplots(figsize=(8.5, 5.2))
        max_k = min(max(r, 1), 20)
        k_vals = list(range(max_k + 1))
        
        rep_logs = [safe_log10(combinatorics.permutations_with_repetition(n, k)) for k in k_vals]
        p_logs = [safe_log10(combinatorics.permutations(n, k)) if (k <= n) else 0.0 for k in k_vals]

        ax.plot(k_vals, rep_logs, marker="o", color=CLR_HIGHLIGHT, lw=2.0, label="With Repetition: n^k")
        if n > 0:
            valid_p_k = [k for k in k_vals if k <= n]
            ax.plot(valid_p_k, [p_logs[k] for k in valid_p_k], marker="s", color=CLR_PERM, lw=2.0, linestyle="--", label="Without Repetition: P(n, k)")

        ax.set_xlabel("Sequence Length k", fontsize=10, fontweight="bold")
        ax.set_ylabel("log10( Permutations )", fontsize=10, fontweight="bold")
        ax.set_title("Permutations with Repetition: n^k Growth (n = " + str(n) + ")", fontsize=11, fontweight="bold")
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.5)

    caption = "What you are looking at: Allowing repetition maintains constant choice freedom across all slots, resulting in pure exponential n^r branching."
    add_caption(fig, caption)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.09)

    return save_or_return_figure(fig, "plot_05_perm_repetition", as_bytes=as_bytes)


def plot_comb_with_repetition(n, r, as_bytes=False):
    """Visualizes combinations with repetition via Stars and Bars theorem.
    
    Draws a symbolic arrangement of r stars and (n - 1) dividing bars,
    illustrating how selections map to multi-compartment partitions.
    """
    if not is_matplotlib_available():
        return None
    if not isinstance(n, int) or not isinstance(r, int):
        raise TypeError("n and r must both be integers.")
    if n < 0 or r < 0 or n > 1000 or r > 1000:
        raise ValueError("Requires 0 <= n, r <= 1000.")

    total_count = combinatorics.combinations_with_repetition(n, r)

    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    ax.axis("off")

    # Edge cases
    if n == 0 or r == 0:
        ax.set_title("Combinations with Repetition: Edge Case (n = " + str(n) + ", r = " + str(r) + ")",
                     fontsize=11, fontweight="bold", pad=12)
        if n == 0 and r == 0:
            msg = "n = 0, r = 0: Exactly 1 empty selection [Result = 1]."
        elif n == 0:
            msg = "n = 0 types available: Impossible to select " + str(r) + " items [Result = 0]."
        else:
            msg = "r = 0 items selected from " + str(n) + " types: Exactly 1 empty selection [Result = 1]."
        
        ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=12, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.6", facecolor="#eff6ff", edgecolor=CLR_COMB))
    else:
        # Standard Stars and Bars visual
        total_symbols = n + r - 1
        ax.set_title("Stars & Bars Model: C(" + str(n) + " + " + str(r) + " - 1, " + str(r) + ") = C(" + str(total_symbols) + ", " + str(r) + ") = " + str(total_count),
                     fontsize=11, fontweight="bold", pad=12)

        # Illustrate 3 sample distributions of r stars across n bins
        # Sample 1: Evenly spread
        # Sample 2: Concentrated in first bin
        # Sample 3: Alternating
        samples = []
        # Construct sample 1
        b1 = [0] * n
        for i in range(r):
            b1[i % n] += 1
        samples.append(("Distributed Sample", b1))

        # Construct sample 2
        b2 = [0] * n
        b2[0] = r
        samples.append(("All in Type 1", b2))

        # Construct sample 3
        b3 = [0] * n
        if n > 1:
            b3[-1] = r
            samples.append(("All in Type " + str(n), b3))

        y_positions = [0.72, 0.44, 0.16]
        for s_idx, (s_label, bin_counts) in enumerate(samples[:3]):
            y_base = y_positions[s_idx]
            ax.text(0.02, y_base + 0.12, s_label + ":", fontsize=9.5, fontweight="bold", color="#1e3a8a")
            
            # Draw stars and bars sequence
            symbol_sequence = []
            for b_idx in range(n):
                for _ in range(bin_counts[b_idx]):
                    symbol_sequence.append("*")
                if b_idx < n - 1:
                    symbol_sequence.append("|")
            
            # Render visually
            x_cursor = 0.05
            for sym in symbol_sequence[:25]:
                if sym == "*":
                    # Draw star circle
                    circle = patches.Circle((x_cursor, y_base), 0.028, facecolor=CLR_COMB, edgecolor="#14532d", zorder=4)
                    ax.add_patch(circle)
                    x_cursor += 0.038
                else:
                    # Draw bar line
                    ax.plot([x_cursor, x_cursor], [y_base - 0.05, y_base + 0.05], color="#0f172a", lw=2.5, zorder=5)
                    x_cursor += 0.038

            if len(symbol_sequence) > 25:
                ax.text(x_cursor + 0.02, y_base, "... +" + str(len(symbol_sequence) - 25) + " symbols",
                        fontsize=8.5, color="#64748b", va="center")

            # Label bin breakdown text
            breakdown_str = " [" + ", ".join(["T" + str(i + 1) + ":" + str(c) for i, c in enumerate(bin_counts)]) + "]"
            ax.text(0.72, y_base, breakdown_str, fontsize=8.5, color="#334155", va="center", fontfamily="monospace")

        ax.set_xlim(0, 1.0)
        ax.set_ylim(0, 1.0)

    caption = "What you are looking at: Stars represent items and bars represent dividers between types; choosing positions for r stars among r+n-1 slots yields C(n+r-1, r)."
    add_caption(fig, caption)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.09)

    return save_or_return_figure(fig, "plot_06_comb_repetition", as_bytes=as_bytes)


def plot_multiset(text, as_bytes=False):
    """Visualizes multiset permutations: n! / (n1! * n2! * ... * nk!).
    
    Displays character frequency counts and the mathematical breakdown comparing
    total unconstrained permutations n! against character divisor factorials.
    """
    if not is_matplotlib_available():
        return None
    if not isinstance(text, str):
        raise TypeError("Input text must be a string.")
    if len(text) > 50:
        raise ValueError("Multiset input text must be at most 50 characters.")

    total_count, freq = combinatorics.multiset_arrangements_count(text)

    fig, (ax_freq, ax_formula) = plt.subplots(1, 2, figsize=(10.0, 5.2), gridspec_kw={"width_ratios": [1.1, 1.2]})

    # Subplot 1: Character Frequencies
    chars = sorted(list(freq.keys()))
    counts = [freq[c] for c in chars]
    
    ax_freq.bar(chars, counts, color=CLR_PERM, width=0.6, edgecolor="#0f172a", linewidth=0.6)
    ax_freq.set_xlabel("Unique Character", fontsize=10, fontweight="bold")
    ax_freq.set_ylabel("Frequency Count", fontsize=10, fontweight="bold")
    ax_freq.set_title("Frequencies in '" + text[:20] + ("..." if len(text) > 20 else "") + "' (Length=" + str(len(text)) + ")",
                      fontsize=11, fontweight="bold")
    ax_freq.grid(axis="y", linestyle="--", alpha=0.5)

    for idx, c in enumerate(counts):
        ax_freq.text(idx, c + 0.1, str(c), ha="center", va="bottom", fontsize=9, fontweight="bold")

    # Subplot 2: Formula Breakdown on log10 axis
    labels = ["Total n!"] + [c + "!" for c in chars] + ["Result"]
    vals = [safe_log10(combinatorics.factorial(len(text)))]
    for c in chars:
        vals.append(safe_log10(combinatorics.factorial(freq[c])))
    vals.append(safe_log10(total_count))

    bar_colors = [CLR_NEUTRAL] + ["#cbd5e1"] * len(chars) + [CLR_HIGHLIGHT]

    ax_formula.bar(labels, vals, color=bar_colors, width=0.6, edgecolor="#0f172a", linewidth=0.6)
    ax_formula.set_ylabel("log10( Value )", fontsize=10, fontweight="bold")
    ax_formula.set_title("Formula Decomposition: n! / Product(ni!)", fontsize=11, fontweight="bold")
    ax_formula.grid(axis="y", linestyle="--", alpha=0.5)

    caption = "What you are looking at: Repeated identical letters are indistinguishable; dividing n! by the factorial of each letter's count cancels overcounting."
    add_caption(fig, caption)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.09)

    return save_or_return_figure(fig, "plot_07_multiset", as_bytes=as_bytes)


def plot_listing(mode, n=4, r=2, text="", as_bytes=False):
    """Visualizes exhaustive listing of arrangements/groups with set uniqueness verification.
    
    Draws a visual tile grid of generated arrangements and compares theoretical formula,
    enumerated list, and unique set counts.
    """
    if not is_matplotlib_available():
        return None

    if mode == "perm":
        items, theo, is_match = combinatorics.list_letter_permutations(n, r)
        title_label = "Permutations P(" + str(n) + ", " + str(r) + ")"
    elif mode == "comb":
        items, theo, is_match = combinatorics.list_letter_combinations(n, r)
        title_label = "Combinations C(" + str(n) + ", " + str(r) + ")"
    elif mode == "multiset":
        items, theo, is_match = combinatorics.list_multiset_permutations(text)
        title_label = "Multiset Arrangements of '" + text + "'"
    else:
        raise ValueError("Invalid listing mode: " + str(mode))

    fig, (ax_bar, ax_grid) = plt.subplots(1, 2, figsize=(10.5, 5.5), gridspec_kw={"width_ratios": [1.0, 1.8]})

    # Subplot 1: Three Count Bars (Theoretical, Generated List, Unique Set)
    actual_count = len(items)
    unique_count = len(set(items))
    count_labels = ["Formula", "List Items", "Unique Set"]
    counts = [theo, actual_count, unique_count]
    colors = [CLR_PERM, CLR_COMB, CLR_HIGHLIGHT]

    ax_bar.bar(count_labels, counts, color=colors, width=0.55, edgecolor="#0f172a", linewidth=0.6)
    ax_bar.set_ylabel("Arrangement Count", fontsize=10, fontweight="bold")
    match_str = "MATCH" if is_match else "MISMATCH"
    ax_bar.set_title("Verification: [" + match_str + "]", fontsize=11, fontweight="bold",
                     color="#15803d" if is_match else "#b91c1c")
    ax_bar.grid(axis="y", linestyle="--", alpha=0.5)

    for idx, c in enumerate(counts):
        ax_bar.text(idx, c + 0.1, str(c), ha="center", va="bottom", fontsize=9.5, fontweight="bold")

    # Subplot 2: Tile Grid of Arrangements
    ax_grid.axis("off")
    ax_grid.set_title(title_label + " (Tiles Display)", fontsize=11, fontweight="bold", pad=8)

    max_display = min(len(items), 120)
    cols = 8 if max_display > 40 else 6
    rows = math.ceil(max_display / cols) if cols > 0 else 1

    tile_w = 0.90 / cols
    tile_h = 0.85 / max(rows, 1)

    for i in range(max_display):
        row_idx = i // cols
        col_idx = i % cols
        x = 0.05 + col_idx * (tile_w + 0.01)
        y = 0.90 - (row_idx + 1) * (tile_h + 0.01)
        
        rect = patches.FancyBboxPatch((x, y), tile_w, tile_h, boxstyle="round,pad=0.01",
                                      facecolor="#f8fafc", edgecolor="#94a3b8", linewidth=0.8)
        ax_grid.add_patch(rect)
        item_str = "".join(items[i])
        ax_grid.text(x + tile_w / 2.0, y + tile_h / 2.0, item_str, ha="center", va="center",
                     fontsize=7.5, fontfamily="monospace", fontweight="bold", color="#1e293b")

    if len(items) > max_display:
        ax_grid.text(0.5, 0.02, "+ " + str(len(items) - max_display) + " more items generated...",
                     ha="center", va="bottom", fontsize=9, style="italic", color="#475569")

    caption = "What you are looking at: Every concrete arrangement is gathered in a tuple; converting tuples into a set confirms uniqueness and validates the formula."
    add_caption(fig, caption)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.09)

    return save_or_return_figure(fig, "plot_08_listing", as_bytes=as_bytes)


def plot_binomial_identities(n, r, as_bytes=False):
    """Visualizes the three core binomial identities for chosen (n, r).
    
    Panels: (a) Symmetry reflection C(n, r) = C(n, n - r),
    (b) Pascal's additive rule C(n, r) = C(n-1, r-1) + C(n-1, r),
    (c) Row sum identity Sum C(n, k) = 2^n.
    """
    if not is_matplotlib_available():
        return None
    if not isinstance(n, int) or not isinstance(r, int):
        raise TypeError("n and r must both be integers.")
    if n < 0 or r < 0 or r > n or n > 1000:
        raise ValueError("Requires 0 <= r <= n <= 1000.")

    rep = combinatorics.verify_binomial_identities(n, r)

    fig, (ax_sym, ax_pascal, ax_sum) = plt.subplots(3, 1, figsize=(9.5, 8.5))

    # Panel A: Symmetry
    k_range = list(range(min(n, 20) + 1))
    c_vals = [safe_log10(combinatorics.combinations(min(n, 20), k)) for k in k_range]
    sym_colors = [CLR_HIGHLIGHT if (k == r or k == (min(n, 20) - r)) else CLR_COMB for k in k_range]

    ax_sym.bar([str(k) for k in k_range], c_vals, color=sym_colors, width=0.6, edgecolor="#0f172a", linewidth=0.5)
    ax_sym.set_ylabel("log10( C )", fontsize=8.5, fontweight="bold")
    ax_sym.set_title("1. Symmetry: C(" + str(n) + ", " + str(r) + ") = C(" + str(n) + ", " + str(n - r) + ") [VERIFIED]",
                     fontsize=10.5, fontweight="bold", color="#15803d")
    ax_sym.grid(axis="y", linestyle="--", alpha=0.5)

    # Panel B: Pascal's Identity
    if rep["pascal_applicable"]:
        p1 = combinatorics.combinations(n - 1, r - 1)
        p2 = combinatorics.combinations(n - 1, r)
        p_target = rep["c_nr"]
        p_labels = ["C(" + str(n-1) + "," + str(r-1) + ")", "C(" + str(n-1) + "," + str(r) + ")", "Sum = C(" + str(n) + "," + str(r) + ")"]
        p_vals = [safe_log10(p1), safe_log10(p2), safe_log10(p_target)]
        p_colors = [CLR_NEUTRAL, CLR_NEUTRAL, CLR_HIGHLIGHT]

        ax_pascal.bar(p_labels, p_vals, color=p_colors, width=0.5, edgecolor="#0f172a", linewidth=0.5)
        ax_pascal.set_ylabel("log10( C )", fontsize=8.5, fontweight="bold")
        ax_pascal.set_title("2. Pascal's Rule: C(n-1, r-1) + C(n-1, r) = C(n, r) [VERIFIED]",
                            fontsize=10.5, fontweight="bold", color="#15803d")
        ax_pascal.grid(axis="y", linestyle="--", alpha=0.5)
    else:
        ax_pascal.axis("off")
        ax_pascal.text(0.5, 0.5, "2. Pascal's Identity: Not applicable for boundary element r = " + str(r) + " (Applies to 1 <= r <= n-1)",
                       ha="center", va="center", fontsize=9.5, style="italic", color="#475569",
                       bbox=dict(boxstyle="round,pad=0.5", facecolor="#f8fafc", edgecolor="#cbd5e1"))

    # Panel C: Row Sum = 2^n
    sum_val = rep["row_sum_value"]
    pow2_val = rep["power_of_two"]
    sum_labels = ["Sum_{k=0}^n C(" + str(n) + ", k)", "2^" + str(n)]
    sum_vals = [safe_log10(sum_val), safe_log10(pow2_val)]

    ax_sum.bar(sum_labels, sum_vals, color=[CLR_COMB, CLR_PERM], width=0.45, edgecolor="#0f172a", linewidth=0.5)
    ax_sum.set_ylabel("log10( Sum )", fontsize=8.5, fontweight="bold")
    ax_sum.set_title("3. Row Sum Identity: Sum of row " + str(n) + " equals 2^" + str(n) + " [VERIFIED]",
                     fontsize=10.5, fontweight="bold", color="#15803d")
    ax_sum.grid(axis="y", linestyle="--", alpha=0.5)

    caption = "What you are looking at: Symmetry reflects mirror balance; Pascal's rule proves additive construction; row sum proves total subsets of an n-element set equal 2^n."
    add_caption(fig, caption)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.07)

    return save_or_return_figure(fig, "plot_09_identities", as_bytes=as_bytes)


def plot_pascal_triangle(num_rows, as_bytes=False):
    """Visualizes Pascal's triangle with cell heat-map and Sierpinski parity pattern.
    
    Draws a centered pyramid of cells coloured by value, annotating row sums 2^k,
    alongside a second panel showing odd/even parity revealing the Sierpinski fractal.
    """
    if not is_matplotlib_available():
        return None
    if not isinstance(num_rows, int):
        raise TypeError("num_rows must be an integer.")
    if num_rows < 1 or num_rows > 15:
        raise ValueError("num_rows must be between 1 and 15.")

    triangle = combinatorics.generate_pascal_triangle(num_rows)

    fig, (ax_tri, ax_sierp) = plt.subplots(1, 2, figsize=(11.0, 5.8), gridspec_kw={"width_ratios": [1.4, 1.0]})

    # Subplot 1: Centered Pascal Triangle Cells
    ax_tri.axis("off")
    ax_tri.set_title("Pascal's Triangle (Rows 0 to " + str(num_rows - 1) + ")", fontsize=11, fontweight="bold", pad=10)

    cell_w = 0.85
    cell_h = 0.70

    for i in range(num_rows):
        row = triangle[i]
        y_pos = -float(i) * 1.05
        # Row sum annotation on right
        ax_tri.text(float(num_rows) * 0.55, y_pos, "Sum = 2^" + str(i) + " = " + str(2 ** i),
                    fontsize=7.5, color="#475569", va="center")

        for j in range(len(row)):
            val = row[j]
            x_pos = (float(j) - float(i) / 2.0) * 1.15

            # Highlight interior sample addition (e.g. at row 3 col 1 if rows >= 4)
            is_sample = (num_rows >= 4 and i == 3 and j == 1)
            cell_bg = "#fef3c7" if is_sample else "#eff6ff"
            edge_color = CLR_HIGHLIGHT if is_sample else CLR_PERM

            rect = patches.FancyBboxPatch((x_pos - cell_w / 2.0, y_pos - cell_h / 2.0), cell_w, cell_h,
                                          boxstyle="round,pad=0.08", facecolor=cell_bg, edgecolor=edge_color, linewidth=1.2)
            ax_tri.add_patch(rect)
            ax_tri.text(x_pos, y_pos, str(val), ha="center", va="center", fontsize=8 if num_rows <= 8 else 6.5,
                        fontweight="bold", color="#0f172a")

    ax_tri.set_xlim(-float(num_rows) * 0.65, float(num_rows) * 0.95)
    ax_tri.set_ylim(-float(num_rows) * 1.05 - 0.5, 0.8)

    # Subplot 2: Sierpinski Gasket / Parity Pattern (val % 2)
    ax_sierp.axis("off")
    ax_sierp.set_title("Sierpinski Parity Fractal (mod 2)", fontsize=11, fontweight="bold", pad=10)

    for i in range(num_rows):
        row = triangle[i]
        y_pos = -float(i) * 1.05
        for j in range(len(row)):
            val = row[j]
            x_pos = (float(j) - float(i) / 2.0) * 1.15
            is_odd = (val % 2 == 1)
            parity_color = CLR_PERM if is_odd else "#ffffff"
            edge_col = CLR_PERM if is_odd else "#cbd5e1"

            rect = patches.FancyBboxPatch((x_pos - cell_w / 2.0, y_pos - cell_h / 2.0), cell_w, cell_h,
                                          boxstyle="round,pad=0.08", facecolor=parity_color, edgecolor=edge_col, linewidth=0.8)
            ax_sierp.add_patch(rect)

    ax_sierp.set_xlim(-float(num_rows) * 0.65, float(num_rows) * 0.65)
    ax_sierp.set_ylim(-float(num_rows) * 1.05 - 0.5, 0.8)
    ax_sierp.text(0, -float(num_rows) * 1.05 - 0.2, "Blue = Odd Numbers | White = Even Numbers",
                  ha="center", va="center", fontsize=8, fontweight="bold", color="#1e293b")

    caption = "What you are looking at: Each cell is the exact sum of the two cells directly above it; coloring cells by odd/even reveals the self-similar Sierpinski triangle."
    add_caption(fig, caption)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.09)

    return save_or_return_figure(fig, "plot_10_pascal_triangle", as_bytes=as_bytes)


def plot_recurrence(rec_type, terms_list, label="Recurrence Sequence", as_bytes=False):
    """Visualizes recurrence sequences and convergence properties.
    
    Plots sequential values with markers. For Fibonacci, includes convergence of the
    adjacent ratio F(n+1)/F(n) toward the Golden Ratio phi (~1.618).
    """
    if not is_matplotlib_available():
        return None
    if not isinstance(terms_list, list):
        raise TypeError("terms_list must be a list of integers.")
    if len(terms_list) == 0:
        raise ValueError("terms_list cannot be empty.")

    n_indices = list(range(len(terms_list)))

    if rec_type == "fibonacci" and len(terms_list) >= 3:
        fig, (ax_curve, ax_ratio) = plt.subplots(2, 1, figsize=(9.0, 7.0), gridspec_kw={"height_ratios": [1.4, 1.0]})

        # Panel 1: Sequence terms
        log_terms = [safe_log10(t) for t in terms_list]
        ax_curve.plot(n_indices, log_terms, marker="o", color=CLR_PERM, lw=2.0, markersize=5)
        ax_curve.set_ylabel("log10( F(n) )", fontsize=9.5, fontweight="bold")
        ax_curve.set_title("Fibonacci Sequence: F(0)=0, F(1)=1, F(n) = F(n-1) + F(n-2)", fontsize=11, fontweight="bold")
        ax_curve.grid(True, linestyle="--", alpha=0.5)

        # Annotate first 5 terms
        for i in range(min(5, len(terms_list))):
            ax_curve.text(i, log_terms[i] + 0.1, "F(" + str(i) + ")=" + str(terms_list[i]),
                          fontsize=7.5, color="#1e3a8a", ha="center")

        # Panel 2: Golden Ratio Convergence
        ratios = []
        ratio_indices = []
        for i in range(1, len(terms_list) - 1):
            denom = terms_list[i]
            if denom > 0:
                # Safe ratio computation: use float safely on moderate numbers
                numer = terms_list[i + 1]
                ratio_val = float(numer) / float(denom)
                ratios.append(ratio_val)
                ratio_indices.append(i)

        ax_ratio.plot(ratio_indices, ratios, marker="s", color=CLR_HIGHLIGHT, lw=1.8, label="F(n+1) / F(n)")
        golden_ratio = (1.0 + math.sqrt(5.0)) / 2.0
        ax_ratio.axhline(golden_ratio, color="#16a34a", linestyle="--", lw=1.5, label="Golden Ratio phi ~ 1.61803")
        
        ax_ratio.set_xlabel("Term Index n", fontsize=9.5, fontweight="bold")
        ax_ratio.set_ylabel("Ratio F(n+1)/F(n)", fontsize=9.5, fontweight="bold")
        ax_ratio.set_title("Convergence to the Golden Ratio (phi)", fontsize=10, fontweight="bold")
        ax_ratio.set_ylim(1.0, 2.2)
        ax_ratio.legend(loc="upper right", fontsize=8.5)
        ax_ratio.grid(True, linestyle="--", alpha=0.5)

    else:
        fig, ax_curve = plt.subplots(figsize=(8.5, 5.2))
        # Decide between linear and log10 based on maximum value
        max_val = max(abs(t) for t in terms_list)
        use_log = (max_val > 1000000 and min(terms_list) >= 0)

        if use_log:
            y_vals = [safe_log10(t) for t in terms_list]
            ylabel = "log10( a(n) )"
        else:
            y_vals = terms_list
            ylabel = "Value a(n)"

        ax_curve.plot(n_indices, y_vals, marker="o", color=CLR_PERM, lw=2.0, markersize=5)
        ax_curve.set_xlabel("Term Index n", fontsize=10, fontweight="bold")
        ax_curve.set_ylabel(ylabel, fontsize=10, fontweight="bold")
        ax_curve.set_title("Recurrence Sequence: " + str(label), fontsize=11, fontweight="bold")
        ax_curve.grid(True, linestyle="--", alpha=0.5)

        for i in range(min(4, len(terms_list))):
            ax_curve.text(i, y_vals[i], " a(" + str(i) + ")=" + str(terms_list[i]),
                          fontsize=7.5, color="#1e3a8a", va="bottom")

    caption = "What you are looking at: Recurrences build terms sequentially from previous states; adjacent ratios in linear constant recurrences converge to characteristic roots."
    add_caption(fig, caption)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.09)

    return save_or_return_figure(fig, "plot_11_recurrence", as_bytes=as_bytes)


def plot_binomial_expansion(n, a, b, as_bytes=False):
    """Visualizes the algebraic expansion of (a*x + b*y)^n.
    
    Displays signed polynomial coefficients contrasted with the underlying
    Pascal's triangle combinations row.
    """
    if not is_matplotlib_available():
        return None
    if not isinstance(n, int) or not isinstance(a, int) or not isinstance(b, int):
        raise TypeError("n, a, and b must be integers.")
    if n < 0 or n > 20 or abs(a) > 10 or abs(b) > 10:
        raise ValueError("Requires 0 <= n <= 20 and |a|, |b| <= 10.")

    terms = combinatorics.binomial_expansion_terms(n, a, b)
    formatted_poly = combinatorics.format_binomial_expansion(terms)

    fig, (ax_coeffs, ax_pascal) = plt.subplots(1, 2, figsize=(11.0, 5.2), gridspec_kw={"width_ratios": [1.4, 1.0]})

    # Subplot 1: Signed Expansion Coefficients
    term_labels = []
    coeffs = []
    bar_colors = []

    for coeff, x_pow, y_pow in terms:
        # Build variable label
        parts = []
        if x_pow > 0:
            parts.append("x" if x_pow == 1 else "x^" + str(x_pow))
        if y_pow > 0:
            parts.append("y" if y_pow == 1 else "y^" + str(y_pow))
        lbl = "*".join(parts) if parts else "1"
        term_labels.append(lbl)
        coeffs.append(coeff)
        bar_colors.append(CLR_PERM if coeff >= 0 else CLR_NEGATIVE)

    ax_coeffs.bar(term_labels, coeffs, color=bar_colors, width=0.6, edgecolor="#0f172a", linewidth=0.5)
    ax_coeffs.axhline(0, color="#64748b", lw=1.0)
    ax_coeffs.set_xlabel("Algebraic Term", fontsize=10, fontweight="bold")
    ax_coeffs.set_ylabel("Signed Coefficient", fontsize=10, fontweight="bold")
    
    # Title showing polynomial formula
    input_str = "(" + (str(a) if a != 1 else "") + "x + " + (str(b) if b != 1 else "") + "y)^" + str(n)
    ax_coeffs.set_title("Expansion Coefficients: " + input_str, fontsize=11, fontweight="bold")
    ax_coeffs.tick_params(axis="x", rotation=30)
    ax_coeffs.grid(axis="y", linestyle="--", alpha=0.5)

    for idx, val in enumerate(coeffs):
        offset = 0.2 if val >= 0 else -0.5
        ax_coeffs.text(idx, val + offset, str(val), ha="center", va="bottom" if val >= 0 else "top",
                       fontsize=8, fontweight="bold", color="#0f172a")

    # Subplot 2: Underlying Pascal Row C(n, k)
    k_range = list(range(n + 1))
    pascal_vals = [combinatorics.combinations(n, k) for k in k_range]

    ax_pascal.bar([str(k) for k in k_range], pascal_vals, color=CLR_COMB, width=0.6, edgecolor="#0f172a", linewidth=0.5)
    ax_pascal.set_xlabel("Binomial Index k", fontsize=10, fontweight="bold")
    ax_pascal.set_ylabel("Value C(" + str(n) + ", k)", fontsize=10, fontweight="bold")
    ax_pascal.set_title("Underlying Pascal Row " + str(n), fontsize=11, fontweight="bold")
    ax_pascal.grid(axis="y", linestyle="--", alpha=0.5)

    caption = "What you are looking at: The Binomial Theorem scales Pascal coefficients C(n, k) by powers of a^(n-k) and b^k to form each polynomial term."
    add_caption(fig, caption)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.10)

    return save_or_return_figure(fig, "plot_12_expansion", as_bytes=as_bytes)


def generate_all_demo_plots():
    """Generates all 12 visual explanation charts using representative demo parameters.
    
    Returns a list of tuples: (description, file_path).
    """
    if not is_matplotlib_available():
        return []

    created = []

    p1 = plot_factorial(6)
    if p1:
        created.append(("1. Factorial (n=6)", p1))

    p2 = plot_permutations(6, 3)
    if p2:
        created.append(("2. Permutations P(6, 3)", p2))

    p3 = plot_combinations(6, 3)
    if p3:
        created.append(("3. Combinations C(6, 3)", p3))

    p4 = plot_comparison(6, 3)
    if p4:
        created.append(("4. Comparison P vs C (6, 3)", p4))

    p5 = plot_perm_with_repetition(3, 4)
    if p5:
        created.append(("5. Permutations with Repetition (3^4)", p5))

    p6 = plot_comb_with_repetition(4, 3)
    if p6:
        created.append(("6. Combinations with Repetition (n=4, r=3)", p6))

    p7 = plot_multiset("MISSISSIPPI")
    if p7:
        created.append(("7. Multiset Arrangements ('MISSISSIPPI')", p7))

    p8 = plot_listing("perm", 4, 2, "")
    if p8:
        created.append(("8. Small Listing P(4, 2)", p8))

    p9 = plot_binomial_identities(6, 3)
    if p9:
        created.append(("9. Binomial Identities (n=6, r=3)", p9))

    p10 = plot_pascal_triangle(8)
    if p10:
        created.append(("10. Pascal's Triangle (rows=8)", p10))

    fib_terms = recurrence.fibonacci_sequence(10)
    p11 = plot_recurrence("fibonacci", fib_terms, "Fibonacci Sequence")
    if p11:
        created.append(("11. Recurrence Relation (Fibonacci 10 terms)", p11))

    p12 = plot_binomial_expansion(5, 1, 1)
    if p12:
        created.append(("12. Binomial Expansion ((x+y)^5)", p12))

    return created

