# Python Historical Exam Question Predictor & Adaptive Quiz Bank

A complete, production-grade academic system built in **100% Python** using **Streamlit**, designed for university computer science and engineering coursework. It extracts, deduplicates, and analyzes past examination papers over a 4–5 year window, calculates deterministic question repetition likelihoods, and provides an interactive practice quiz portal with diagnostic analytics.

---

## 🌟 Key Features

### 1. Ingestion & Preprocessing Pipeline
- **Dual PDF Intake**: Supports direct PDF file uploads or public Google Drive URLs via `gdown`.
- **Text & OCR Fallback**: Native PDF stream extraction with `PyMuPDF` (`fitz`), automatically falling back to `pytesseract` for scanned or low-glyph pages.
- **Visual Element Cropping**: Embedded diagrams, schematics, and charts are detected, cropped, and saved to `assets/diagrams/`.
- **Perceptual Diagram Hashing**: 64-bit `pHash` via `imagehash` with Hamming distance clustering ($\le 5$ bits) to link recurring diagrams across different exam years.
- **Confidence Scoring & Review Queue**: Extraction confidence is scored; questions scoring $< 80\%$ or missing marks are automatically routed to the Admin Review Queue.

### 2. Deterministic Prediction Engine (Zero ML)
- **Fuzzy Text Deduplication**: Groups semantically similar questions using `RapidFuzz` Token Sort Ratio ($\ge 85\%$).
- **Multi-Factor Heuristic Formula**:
  $$\text{Score}(C) = w_f \cdot \hat{F}(C) + w_r \cdot \hat{R}(C) + w_g \cdot \hat{G}(C) + w_m \cdot \hat{M}(C)$$
  - **Frequency ($\hat{F}$)**: Total appearances over the historical observation window.
  - **Recency ($\hat{R}$)**: Exponential decay weighting ($\lambda = 0.3$) prioritizing recent exam years.
  - **Gap Analysis ($\hat{G}$)**: Awards a cyclical boost for questions absent 1–2 years following historical rotation cycles.
  - **Marks Weight ($\hat{M}$)**: Normalizes question weight relative to syllabus maximums.
  - **Categorization**: High ($\ge 70\%$), Medium ($45 - 69\%$), and Low ($< 45\%$) likelihood badges.

### 3. Student Adaptive Quiz & Diagnostics
- **5-Option MCQ Format**: Options A, B, C, D, plus **Option E**: *"🚫 Not in my syllabus / Skip"*.
- **Non-Penalizing Skip Logic**: Option E excludes questions from topic accuracy denominators, ensuring student diagnostic metrics remain untainted.
- **Diagnostic Matrix**: Calculates Revision Priority Score ($P = (1 - \text{Accuracy}) \times \text{Exam Likelihood}$).
- **1-Click Remedial Quiz**: Immediately launches a focused retry quiz containing only questions answered incorrectly.

### 4. Admin Portal & Glowing Tag Management
- **Restricted Access**: Hardcoded server-side authorization bound to `diyanshah2301@gmail.com`.
- **Glowing Green/Black Toggle Tags**: Multi-select tag buttons featuring customized CSS styling (`#28a745` background, black text, and soft glowing drop-shadows).
- **Tag Palette Manager**: Add, merge, and deactivate vocabulary tags across the entire question bank.

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

*(Note: For scanned PDF OCR support, ensure [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) is installed on your operating system.)*

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

## 🔒 Security & Admin Access
To access the Administrator Management Portal:
1. Open the sidebar and click **🔑 Login / Admin Access** -> **Admin Login**.
2. Enter `diyanshah2301@gmail.com` and passcode `admin123`.
3. The **🛡️ Admin Management Portal** menu will now appear in your sidebar navigation.
