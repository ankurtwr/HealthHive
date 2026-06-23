# Project Architecture & Codebase Guide: HealthHive

Welcome to the comprehensive codebase guide for **HealthHive**, an intelligent medicine price comparison and generic alternative recommendation platform. This document covers the tech stack, file structure, database tables, modules, functions, and key architectural choices in detail.

---

## 🛠️ Technology Stack & Tools Used

The HealthHive platform is engineered using modern, robust, and lightweight technologies designed for performance, flexibility, and scalability.

1. **Flask (Python 3)**:
   - **Why we used it:** Used as the core web framework. Its micro-architectural design allows us to structure the application using the factory pattern, register components using Blueprints, and avoid unnecessary overhead while retaining maximum control over request handling.
2. **Gunicorn (WSGI Server)**:
   - **Why we used it:** A production-ready Python WSGI HTTP server. It manages multiple worker processes to handle concurrent user requests efficiently on the EC2 server, interfacing with Nginx.
3. **Nginx (Reverse Proxy & Web Server)**:
   - **Why we used it:** Placed at the entry point of the EC2 instance to serve static files (`/static`) directly (bypassing Gunicorn for high performance), handle SSL termination, and act as a secure reverse proxy to forward client HTTP requests to Gunicorn via a Unix socket.
4. **MariaDB / MySQL**:
   - **Why we used it:** Provides transactional data storage. Relational tables enable structured indexing on brand names and salt compositions, allowing fast queries and foreign keys with cascade deletions.
5. **Google Gemini API (Google GenAI Client)**:
   - **Why we used it:** Powering two core features:
     - **Image Search OCR:** Recognizes and extracts medicine names from uploaded prescription/strip photos.
     - **Health Assistant Chatbot:** Engages in natural conversations, answers queries, and helps users understand generic alternatives.
6. **Pytesseract (Tesseract OCR Fallback)**:
   - **Why we used it:** Placed as an offline fallback. If the Gemini API key is missing or encounters a rate limit, the system uses Tesseract to perform local Optical Character Recognition (OCR) on uploaded files.
7. **Requests (HTTP Client)**:
   - **Why we used it:** Used in the price scraper to make concurrent, lightweight PWA API requests and HTML page fetches to Tata 1mg, Netmeds, and PharmEasy.
8. **Flask-Login**:
   - **Why we used it:** Manages session-based user authentication, securely tracking logged-in states, logins, and logouts.
9. **Flask-WTF & WTForms**:
   - **Why we used it:** Handles form generation and secure CSRF (Cross-Site Request Forgery) protection on the backend, validating user inputs for login, registration, and search forms.

---

## 📂 File Architecture & Modules

Below is the directory structure and the details of what each file is responsible for.

```
HealthHive/
├── app.py                   # Application factory and configuration
├── wsgi.py                  # WSGI entry point for Gunicorn
├── config.py                # Environment configuration loader
├── db.py                    # Database connection manager
├── models.py                # User database model
├── forms.py                 # Form validation classes
├── price_scraper.py         # Web scrapers for online pharmacy prices
├── medicine_service.py      # Core search and savings logic
├── understand.md            # [NEW] Detailed codebase documentation
├── deploy/                  # Deployment assets
│   ├── setup.sh             # Server setup script (Amazon Linux)
│   ├── deploy.sh            # Quick update script
│   ├── healthhive.service   # systemd service configuration
│   └── nginx_healthhive.conf# Nginx server block configuration
├── static/                  # Client-side static assets
│   ├── css/
│   │   └── main.css         # Main stylesheet (with light/dark tokens)
│   └── js/
│       └── main.js          # Autocomplete, Chatbot, and Theme switcher
├── templates/               # Jinja2 HTML templates
│   ├── base.html            # Main base wrapper with chatbot and navbar
│   ├── auth/                # Login, registration, and logout templates
│   ├── main/                # Dashboard, Profile, and Terms templates
│   └── search/              # Medicine and generic search templates
└── scripts/                 # System scripts
    ├── fetch_janaushadhi.py # PMBJP dataset importer
    └── ocr.ps1              # Local OCR utility script
```

---

## 💾 Database Schema

The relational database is configured under the name `medcompare`. Here is the purpose of each table:

1. **`users`**:
   - Stores account credentials (`username`, `email`, `password_hash`).
   - Tracks terms and conditions acceptance (`accepted_terms`, `accepted_terms_at`).
2. **`medicines`**:
   - Stores the base catalog of branded medicines imported from the CDSCO database (`brand_name`, `salt_composition`, `manufacturer`, `dosage_form`, `strength`).
3. **`generics`**:
   - Stores generic medicine alternatives, including the Pradhan Mantri Bhartiya Janaushadhi Pariyojana (PMBJP) store items (`salt_composition`, `generic_name`, `mrp`, `pack_size`, `source`, `jan_aushadhi_code`).
4. **`price_cache`**:
   - Caches scraped online pharmacy price data (`platform`, `price`, `mrp`, `discount_pct`, `product_url`, `pack_size`, `manufacturer`, `image_url`, `fetched_at`) linked to `medicines.id`. Caching optimizes response times and prevents IP bans from commercial platforms.
5. **`search_history`**:
   - Logs searches conducted by users to provide suggestions and statistics on their profiles.
6. **`user_prescriptions`**:
   - Tracks OCR prescription image uploads (`file_path`, `extracted_text`).
7. **`user_medicines`**:
   - Links users to saved medicines for quick profile access.
8. **`medicine_reminders`**:
   - Manages dosage scheduling alerts configured by the user (`dosage`, time checks, `is_active`).

---

## ⚙️ Module Breakdown & Core Functions

### 1. `db.py` (Database Connector)
* **`get_connection()`**: Establishes a raw connection to the MariaDB/MySQL database using config variables.
* **`query_one(query, params)`**: Executes a query and returns the first row as a dictionary, closing the cursor.
* **`query_all(query, params)`**: Executes a query and returns all matching rows as a list of dictionaries.
* **`execute(query, params)`**: Runs INSERT, UPDATE, or DELETE operations and commits changes.

### 2. `price_scraper.py` (Dynamic Scraper Engine)
* **`get_live_prices(medicine_name)`**: Orchestrates the live price search. It checks the database cache first (valid for 4 hours); on a cache miss, it calls platform-specific scrapers, filters, sorts them by price, saves them to cache, and returns the list.
* **`_calculate_match_score(query, name)`**: 
  - **How it works:** Splits query and product name into alphanumeric tokens. Evaluates exact-word overlap and prefix matches. Computes an overall similarity ratio (`SequenceMatcher`) and applies score multipliers. Heavy penalties are applied if the primary search term does not match the product name's starting word. This prevents false positive matches (e.g., matching "Dolo" to "Dologel").
* **`_extract_price_by_class(html, class_keyword)`**:
  - **How it works:** Scans raw HTML for a tag whose class attribute contains the `class_keyword`. Extracts its inner HTML, sanitizes it by stripping comments (`<!--...-->`) and sub-tags (`<...>`), and uses regex to extract the first valid decimal number. This fixes matching errors caused by structural variations (like PharmEasy’s comment separators).
* **`_fetch_1mg(medicine_name, medicine_id)`**: Queries Tata 1mg's PWA search API, filters results to `type == 'drug'`, scores matches, and resolves direct prices.
* **`_fetch_netmeds(medicine_name, medicine_id)`**: Downloads Netmeds search pages, extracts `window.__INITIAL_STATE__` JSON payload containing search listings, scores the items, and returns the product URL and pricing.
* **`_fetch_pharmeasy(medicine_name, medicine_id)`**: Queries PharmEasy search API, matches listings, and requests the product page HTML to scrape exact pricing and packaging details.

### 3. `medicine_service.py` (Internal Search Coordinator)
* **`search_medicine(query_str)`**: Performs a search chain:
  1. Checks for exact brand name matches in `medicines`.
  2. Fallback to wildcard substring (`LIKE`) brand matching.
  3. Fallback to salt/composition matches.
  4. Queries matching generic options (`generics`), prioritizing government `JanAushadhi` sources.
  5. Identifies alternative competitor brands (`other_brands`) with the same salt.
  6. Calculates potential savings against the brand's MRP.
* **`get_suggestions(prefix)`**: Returns up to 8 matching brand names starting with `prefix` for AJAX-powered autocomplete.

---

## 🎨 Theme Toggle & Appearance Implementation

The user interface supports a seamless toggle between **Dark Mode (Default)** and **Light Mode**.

1. **Anti-Flash Implementation (`templates/base.html`)**:
   - An IIFE script is embedded in the `<head>` of `base.html`. It reads `localStorage.getItem('theme')` immediately.
   - If set to `light`, it adds the `.light-theme` class to `document.documentElement` **before** the page content parses. This prevents the white flash effect on dark screens when browsing.
2. **Variables Mapping (`static/css/main.css`)**:
   - Color tokens are defined globally using CSS custom properties (`--bg`, `--text`, `--border`, etc.) inside `:root`.
   - When `.light-theme` is active, the variables are overridden with high-contrast, harmonious light variables (white panels, slate borders, deep dark text).
3. **Toggle Handler (`static/js/main.js`)**:
   - Watches clicks on the navbar button `#theme-toggle-btn`. It toggles `.light-theme` on the root node and updates the indicator icon (`☀️` vs `🌙`) and `localStorage` to persist selection.
4. **Light Mode Hover Contrast & Readability Enhancements (`static/css/main.css`)**:
   - Optimized autocomplete item hover background states (`#e2e8f0`) and chips to ensure text is fully legible.
   - Refined generic cards and price comparison cards interactive hover background transitions.
   - Set high-contrast overrides for user chat bubble text (`#ffffff !important`) to keep standard readability on green gradients.

### 4. Search Fallback to Live Scraper for Database Omissions
- **How it works:** In `medicine_service.py`, when a searched medicine is not found in the local database, the coordinator builds a `mock_medicine` object with default labels and sets `found: True` and `not_in_db: True`.
- **UI Integration:** The template [search.html](file:///c:/Users/Anuj/Desktop/HealthHive/templates/search/search.html) displays a warning box informing the user of the database omission while rendering the comparisons container, which seamlessly queries the live online pharmacy prices for the custom query. Correct database spelling suggestions are also offered inside this alert.
