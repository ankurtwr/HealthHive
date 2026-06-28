# HealthHive: Intelligent Generic Medicine Recommender & Price Comparator 
#http://15.206.74.125

HealthHive is a comprehensive web application designed to help users find affordable generic alternatives to expensive branded medicines, compare live prices across multiple e-pharmacies, and make informed healthcare decisions using AI-driven tools.

## Features
- **Generic Alternatives Search**: Matches expensive branded medicines to affordable generic alternatives (especially PMBJP / Jan Aushadhi).
- **Live Price Comparison**: Scrapes live prices from top e-pharmacies (Tata 1mg, Netmeds, PharmEasy) with local caching.
- **Image-based Search (OCR)**: Upload a photo of a medicine strip and the system will extract the text using OpenCV & Tesseract to find alternatives.
- **AI Chatbot**: Built-in chatbot assistant to quickly answer queries regarding medicines and their generic equivalents.
- **Responsive UI**: Premium, dark-mode focused UI with interactive dashboards and search history.

## Setup Instructions

1. **Clone the repository**
2. **Create a virtual environment & install dependencies**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Database Configuration**:
   - Install MySQL and create a database named `medcompare`.
   - Run `schema.sql` to setup tables.
   - Run `python seed_sample.py` and `python scripts/fetch_janaushadhi.py` to ingest the initial dataset.
4. **Tesseract OCR (Windows)**:
   - For the Image Search feature to work, download and install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki).
   - Ensure it is installed at `C:\Program Files\Tesseract-OCR\tesseract.exe` or update the path in `routes/image_search.py`.
5. **Run the Application**:
   ```bash
   python app.py
   ```
   Navigate to `http://127.0.0.1:5000`

## System Architecture & Details
See the `RESEARCH_PAPER.md` for an in-depth technical analysis of the project.
