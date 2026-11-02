# Resume IQ — AI Resume Analyzer & Skill Gap Roadmap
> **"Analyze your resume. Discover your gaps. Build your skills. Become job-ready."**

Built for **Hackfest 3.0**, **Resume IQ** is an end-to-end AI career assistance platform for students, freshers, and job seekers. Unlike basic keyword counters, Resume IQ performs deep NLP-based parsing, semantic job-description matching, ATS compatibility audits, radar-chart skill gap visualizers, multi-role career comparisons, and personalized, step-by-step learning roadmaps with full state persistence.

---

## 🌟 The 6 Mandatory Core Features

1. **AI-Powered Resume Analysis**
   - High-fidelity PDF & DOCX text parsing (PyMuPDF, pdfplumber, python-docx).
   - Extraction and categorization of technical & soft skills, education, experience, and projects.
   - Comprehensive score calculations: Overall Quality, Skills, Experience, Keywords, ATS, and Formatting (out of 100).
   - Actionable strengths, weaknesses, and improvement recommendations.
   - Persistent across browser refresh and multi-page navigation.

2. **Smart Job Match Score**
   - Compare your active resume directly against real pasted Job Descriptions (JDs) or selected role profiles.
   - Computes weighted score: Required Skills (60%), Preferred Skills (25%), Semantic Text Alignment (15%).
   - Highlights exact matching skills, missing skills, and partial matches with an explainable scoring breakdown.
   - Preserves job match results in SQLite database.

3. **Intelligent Skill Gap Detection**
   - Benchmarks candidate abilities against standard industry profiles: Software Developer, Data Analyst, Web Developer, Machine Learning Engineer, QA Engineer, DevOps, and custom JDs.
   - Visual interactive **Radar Chart** comparing "My Skills" vs. "Required Skills".
   - Identifies high-priority skills that yield the highest hiring impact.
   - Automatically reloads cached gap analyses upon page navigation.

4. **Personalized Learning Roadmap**
   - Generates a customized 4-stage roadmap: **Learn → Practice → Build → Apply** from missing skills.
   - Curated links to free tutorials, practice platforms (LeetCode, Kaggle, HackerRank), and mini-project concepts.
   - Mark-as-completed tasks saved directly in SQLite.
   - **Progress is strictly maintained upon browser refresh and navigation** (no accidental resets).

5. **ATS-Friendly Resume Optimization**
   - Audits resumes against real Applicant Tracking System constraints.
   - Detects problematic characters, symbols, formatting gaps, and missing standard section titles.
   - Delivers before-and-after bullet point transformations utilizing strong action verbs and quantified metrics.

6. **Multi-Job Profile Comparison**
   - Simultaneously compares one resume across 5–8 standard career profiles + custom roles.
   - Interactive horizontal bar chart displaying compatibility across roles.
   - Identifies the candidate's optimal career direction and ranks profiles.
   - Allows users to add and evaluate custom job descriptions.

---

## 🛠️ Technology Stack

- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5, Bootstrap Icons, Chart.js 4.x
- **Backend**: Python 3.9+, Flask, Flask-SQLAlchemy, Flask-CORS, Werkzeug
- **AI & NLP**: Pattern matching, keyword extraction, semantic similarity algorithms, optional Google Gemini API / OpenAI API integration
- **File Parsing**: PyMuPDF (`fitz`), `pdfplumber`, `python-docx`
- **Database**: SQLite (persisted via SQLAlchemy)

---

## 📂 Project Structure

```
ResumeIQ/
├── app.py                      # Flask Application entry point & API endpoints
├── config.py                   # Application configuration & environment loaders
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── .env.example                # Example environment configuration
├── .env                        # Local environment variables
├── .gitignore                  # Git ignore rules
│
├── backend/
│   ├── __init__.py
│   ├── database.py             # SQLAlchemy models (Uploads, Analyses, Matches, Gaps, Roadmaps, Comparisons)
│   ├── resume_parser.py        # PDF & DOCX extraction engine
│   ├── resume_analyzer.py      # Skill classification & scoring engine
│   ├── job_matcher.py          # Semantic & weighted job matching + multi-job comparisons
│   ├── skill_gap.py            # Category matrix & radar calculation
│   ├── ats_optimizer.py        # ATS rule audit & before/after bullets
│   ├── roadmap_generator.py    # 4-stage learning curriculum generator
│   └── ai_service.py           # Gemini/OpenAI API + rule-based NLP fallback
│
├── templates/                  # Jinja2 HTML Templates
│   ├── base.html               # Shared layout & CDN includes
│   ├── index.html              # Futuristic AI SaaS Landing Page
│   ├── dashboard.html          # User Analytics Dashboard
│   ├── analysis.html           # Active resume banner, upload & full analysis page
│   ├── job_match.html          # Job Description matcher page
│   ├── skill_gap.html          # Radar chart skill gap page
│   ├── roadmap.html            # Interactive learning roadmap page
│   └── comparison.html         # Multi-job profile comparison page
│
├── static/
│   ├── css/
│   │   ├── style.css           # Landing page stylesheet & global theme
│   │   └── dashboard.css       # Dashboard layout & component styles
│   └── js/
│       ├── app.js              # Active resume state synchronization & toast alerts
│       ├── dashboard.js        # Feature controllers & API handlers
│       └── charts.js           # Chart.js visualization engine
│
├── tests/
│   └── test_scenarios.py       # Comprehensive 13-scenario automated test suite
└── uploads/                    # Secure local resume storage
```

---

## 🚀 Setup & Execution Guide

### 1. Navigate to Project
```powershell
cd "c:\Users\Sudhir\OneDrive\Desktop\Project ResumeIQ"
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Launch Application
```powershell
python app.py
```
Open your browser and visit:
👉 **`http://localhost:5000`**

---

## 🧪 Automated Test Suite

Run the full end-to-end verification test suite covering all 13 test scenarios:
```powershell
python tests/test_scenarios.py
```
Expected output:
```
=== ALL 13 TEST SCENARIOS PASSED WITH ZERO ERRORS! ===
```

---
*Created for Hackfest 3.0.*
