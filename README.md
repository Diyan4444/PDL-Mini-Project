# Python Historical Exam Question Predictor & Adaptive Quiz Bank

A complete, production-grade academic system built in **100% Python** using **Streamlit**, designed for university computer science and engineering coursework. It extracts, deduplicates, and analyzes past examination papers over a 4–5 year window, calculates deterministic question repetition likelihoods, and provides an interactive practice quiz portal with diagnostic analytics.

---

## 🌟 Key Features

### 1. Ingestion Pipeline & Auto-Segregation
- **Combined Multi-Paper PDF Intake**: Ingest single or concatenated multi-paper PDFs (up to 150 pages / 100 MB). The auto-segregator classifies pages into `FIRST_PAGE`, `CONTINUATION`, and `BLANK`, detects paper boundaries using header table keywords, and slices per-paper PDFs into `data/papers/`.
- **Advanced Computer Vision Preprocessing**:
  - **Deskew**: Detects orientation via text binarization moments and deskews images ($\pm 45^\circ$).
  - **Illumination & Shadow Removal**: Estimates background via morphological dilation/blur and performs background division to flatten scanner shadows and non-uniform lighting.
  - **Artifact & Finger Masking**: Detects and cleans edge scanner shadows and skin tones (HSV $H \in [0, 25], S \in [30, 200], V \in [60, 255]$) within 8% of page boundaries.
  - **Sharpening & Contrast**: Applies CLAHE on luminance and mild unsharp masking for crisp text edges.
- **Dual-Style Question Anchor Detection**:
  - **Prefixed Style**: Matches `Q.1`, `Q.2`, `1(a)`, `2b)` style anchors.
  - **Columnar Table Style**: Automatically parses tables with `Q.Nos`, `Questions`, `Marks`, and `CO` columns. Carries question numbers forward across subparts `b`, `c` and delineates question rows via right-column Marks/CO anchors (`[CO1] [5]`, `[CO2] [7]`, `(5) CO1`).
- **Inter-Page Continuation Resolution**: Resolves questions spanning page breaks (such as text on Page $N$ with its associated graph on the top of Page $N+1$ before the next question), setting `is_continuation = 1` and appending cropped diagram assets.
- **Isolated Figure Detection**: Masks text bounding boxes and table rules to isolate non-text ink components (graphs, circuits, diagrams $\ge 2500\text{ px}^2$), computing a 64-bit perceptual hash (`pHash`) to cluster recurring figures across years.
- **Automated Metadata Extraction**: Extracts course name, course code (e.g. `R5IT2002T`, `R5MA2007T`), exam type (normalized to `midterm` or `endterm`), date, academic year, semester, duration, max marks, and `is_makeup` flag with confidence scoring.

### 2. Deterministic Prediction Engine (Zero ML)
- **Fuzzy Text Deduplication**: Groups semantically similar questions using `RapidFuzz` Token Sort Ratio ($\ge 85\%$).
- **Multi-Factor Heuristic Formula**:
  $$\text{Score}(C) = w_f \cdot \hat{F}(C) + w_r \cdot \hat{R}(C) + w_g \cdot \hat{G}(C) + w_m \cdot \hat{M}(C)$$
  - **Frequency ($\hat{F}$)**: Distinct year appearances over the historical observation window.
  - **Recency ($\hat{R}$)**: Exponential decay weighting ($\lambda = 0.3$) prioritizing recent exam years.
  - **Gap Analysis ($\hat{G}$)**: Awards a cyclical boost for questions absent 1–2 years following historical rotation cycles.
  - **Marks Weight ($\hat{M}$)**: Normalizes question weight relative to syllabus maximums.
  - **Categorization**: High ($\ge 70\%$), Medium ($45 - 69\%$), and Low ($< 45\%$) likelihood badges.

### 3. Student Adaptive Quiz & Diagnostics
- **5-Option MCQ Format**: Options A, B, C, D, plus **Option E**: *"🚫 Not in my syllabus / Skip"*.
- **Verified Question Serving**: Student quizzes serve verified MCQs, ensuring high exam fidelity.
- **Non-Penalizing Skip Logic**: Option E excludes questions from topic accuracy denominators, ensuring student diagnostic metrics remain untainted.
- **Diagnostic Matrix**: Calculates Revision Priority Score ($P = (1 - \text{Accuracy}) \times \text{Exam Likelihood}$).
- **1-Click Remedial Quiz**: Immediately launches a focused retry quiz strictly reusing stored MCQs for identified weak topics.

### 4. Admin Portal & Tag Management
- **Security & Authorization**: Hardcoded server-side authorization strictly bound to `diyanshah2301@gmail.com` with Google OIDC (`st.login`, `st.user.email_verified == True`). Local dev passcode authentication enabled exclusively when `DEV_MODE=1`.
- **Glowing Green/Black Toggle Tags**: Multi-select tag buttons featuring customized CSS styling (`#28a745` background, black text, and soft glowing drop-shadows) using `.st-key-<key> button` selectors.
- **MCQ Verification Queue**: Dedicated administrative queue to review and approve draft MCQs.
- **Orphan Cleanup**: 1-click database maintenance to prune orphaned MCQs and unused diagram groups.

### 5. Extended Lab Presentation Capabilities
- **Back-Testing Engine**: Objectively evaluates prediction accuracy by predicting Year $T$ using solely years $< T$ and computing the empirical hit-rate.
- **Mock Exam Generator**: Generates 40-mark Midterm (Units 1–2) and 100-mark Endterm (Units 1–5) examination blueprints.
- **ReportLab PDF Export**: Downloads printable study sheets with prediction badges and syllabus references.

---

## 🚀 Installation & Setup

### 1. Clone & Enter Directory
```bash
cd "c:\Users\Diyan\Desktop\PDL Lab\Project_pdl"
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Secrets
Edit `.streamlit/secrets.toml`:
```toml
admin_email = "diyanshah2301@gmail.com"
admin_dev_passcode = "admin123"
```

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Running the Pytest Suite
```bash
pytest tests/test_pipeline.py -v
```
Validates the complete end-to-end pipeline against test fixtures:
- DAA camera scan fixture (7 subquestions, 40 marks, Dijkstra continuation, 4 diagram crops).
- Math multi-paper fixture (2 discrete papers, make-up detection).
- Concatenated 6-page multi-paper intake.
- Synthetic image degradation and quality scoring.
- Marks and Course Outcome (CO) edge cases.
- Database migration idempotency.
