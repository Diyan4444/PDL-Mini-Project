# Python Historical Exam Question Predictor & Adaptive Quiz Bank

A complete, production-grade academic system built in **100% Python** using **Streamlit**, designed for university computer science and engineering coursework. It extracts, deduplicates, and analyzes past examination papers over a multi-year window, calculates deterministic question repetition likelihoods, and provides an interactive practice quiz portal with diagnostic analytics.

---

## 🌟 Key Features

### 1. Overview Dashboard
- **Executive Summary Metrics**: High-level view of ingested papers, extracted questions, academic years covered, and verified MCQ bank count.
- **Unit-Wise Distribution Charts**: Interactive bar charts tracking questions per unit and average repetition likelihood per syllabus unit.
- **Top Predicted Questions**: Quick-look preview cards for the highest-likelihood questions across the syllabus.

### 2. Ingestion Pipeline & Auto-Segregation
- **Combined Multi-Paper PDF Intake**: Ingest single or concatenated multi-paper PDFs (up to 150 pages / 100 MB). The auto-segregator classifies pages into `FIRST_PAGE`, `CONTINUATION`, and `BLANK`, detects paper boundaries using header table keywords, and slices per-paper PDFs into `data/papers/`.
- **Advanced Computer Vision Preprocessing**:
  - **Deskew**: Detects orientation via text binarization moments and deskews images ($\pm 45^\circ$).
  - **Illumination & Shadow Removal**: Estimates background via morphological dilation/blur and performs background division to flatten scanner shadows and non-uniform lighting.
  - **Artifact & Finger Masking**: Detects and cleans edge scanner shadows and skin tones (HSV $H \in [0, 25], S \in [30, 200], V \in [60, 255]$) within 8% of page boundaries.
  - **Sharpening & Contrast**: Applies CLAHE on luminance and mild unsharp masking for crisp text edges.
- **Dual-Style Question Anchor Detection**:
  - **Prefixed Style**: Matches `Q.1`, `Q.2`, `1(a)`, `2b)` style anchors.
  - **Columnar Table Style**: Automatically parses tables with `Q.Nos`, `Questions`, `Marks`, and `CO` columns. Carries question numbers forward across subparts `b`, `c` and delineates question rows via right-column Marks/CO anchors (`[CO1] [5]`, `[CO2] [7]`, `(5) CO1`).
- **Inter-Page Continuation Resolution**: Resolves questions spanning page breaks, setting `is_continuation = 1` and appending cropped diagram assets.
- **Isolated Figure Detection**: Masks text bounding boxes and table rules to isolate non-text ink components (graphs, circuits, diagrams $\ge 2500\text{ px}^2$), computing a 64-bit perceptual hash (`pHash`) to cluster recurring figures across years.
- **Automated Metadata Extraction**: Extracts course name, course code (e.g. `R5IT2002T`, `R5MA2007T`), exam type (normalized to `midterm` or `endterm`), date, academic year, semester, duration, max marks, and `is_makeup` flag with confidence scoring.

### 3. Pipeline Inspector (Admin)
- Side-by-side inspection of raw rendered PDF pages (at 110 DPI), preprocessed clean BGR images, and OpenCV bounding box overlays highlighting parsed questions and table cells with their question numbers.

### 4. Deterministic Prediction Engine (Zero ML)
- **Fuzzy Text Deduplication**: Groups semantically similar questions using `RapidFuzz` Token Sort Ratio ($\ge 85\%$).
- **Multi-Factor Heuristic Formula**:
  $$\text{Score}(C) = w_f \cdot \hat{F}(C) + w_r \cdot \hat{R}(C) + w_g \cdot \hat{G}(C) + w_m \cdot \hat{M}(C)$$
  - **Frequency ($\hat{F}$)**: Distinct year appearances over the historical observation window ($w_f = 0.35$).
  - **Recency ($\hat{R}$)**: Exponential decay weighting ($\lambda = 0.3$) prioritizing recent exam years ($w_r = 0.30$).
  - **Gap Analysis ($\hat{G}$)**: Awards a cyclical boost for questions absent 1–2 years following historical rotation cycles ($w_g = 0.20$).
  - **Marks Weight ($\hat{M}$)**: Normalizes question weight relative to syllabus maximums ($w_m = 0.15$).
  - **Categorization**: High ($\ge 70\%$), Medium ($45 - 69\%$), and Low ($< 45\%$) likelihood badges.
- **Data Volume Recommendation**: For reliable predictions, a **minimum of 3 years of papers** is recommended. When fewer years are available, a clear low-data warning is presented and predictions remain indicative.
- **Contribution Breakdown & Export**: Stacked component bars show the exact point contribution of Frequency, Recency, Gap, and Marks, with one-click CSV export.

### 5. Back-Testing Engine (Leak-Free)
- Evaluates prediction accuracy strictly using papers prior to the test year ($Y < T$).
- Features rolling back-tests comparing hit rate against a naive recency baseline over historical exam cycles.

### 6. Student Accounts & Adaptive Quiz Bank
- **Secure Student Authentication**: Salted PBKDF2-HMAC-SHA256 password hashing with registration and login sub-tabs. Student IDs are strictly derived from authenticated accounts.
- **Rule-Based & Verified MCQs**:
  - Deterministic generators create questions testing topic classification (`rule_based_topic`), cognitive task verb identification (`rule_based_task`), and historical repetition (`rule_based_repeat`).
  - Instructors can author verified subject-matter MCQs via the admin portal.
  - Archived legacy placeholder MCQs are preserved in the database for audit integrity but excluded from student quizzes.
- **Adaptive Question Selection**: Biased toward a student's unmastered weak topics while down-weighting questions recently answered correctly.
- **Non-Penalizing Skip Logic**: Option E (*"🚫 Not in my syllabus / Skip"*) cleanly excludes questions from accuracy calculations. All-skipped topics are listed separately without diagnostic penalty.
- **Immediate Feedback & Remedial Flow**: Interactive "Check answer" validation with explanations, timer tracking, and one-click remedial retries for incorrect questions.

### 7. Admin Portal & Security Hardening
- **Dev & Production Authentication**: Constant-time `hmac.compare_digest` passcode checks with brute-force lockout (5 attempts / 60 seconds lockout) in development mode (`DEV_MODE=1`), and Google OIDC in production.
- **Safe HTML Rendering**: All user-derived strings in HTML contexts are sanitized through `safe()` to prevent XSS injection.
- **Orphan Cleanup Safeguards**: Two-stage orphan preview and confirmed cleanup with automatic JSON audit backups saved to `data/backups/`.

---

## 🚀 Installation & Setup

### 1. Clone & Enter Directory
```bash
cd "c:\Users\Diyan\Desktop\PDL Lab\Project_pdl"
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Configure Secrets
Create `.streamlit/secrets.toml` (see `.streamlit/secrets.toml.example`):
```toml
admin_email = "diyanshah2301@gmail.com"
admin_dev_passcode = "your_secure_dev_passcode"
DEV_MODE = "1"
```

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Running Tests & Code Quality

### 1. Run Unit & Regression Tests
```bash
# Run all tests
pytest tests/ -q

# Run regression fix tests
pytest tests/test_fixes.py -v

# Run end-to-end pipeline tests
pytest tests/test_pipeline.py -v
```

### 2. Run Static Analysis (Pyflakes)
```bash
python -m pyflakes modules app.py tests
```
Must exit with return code 0 and zero warnings.
