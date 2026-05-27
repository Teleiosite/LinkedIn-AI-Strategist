# LinkedIn AI Strategist & Automation SaaS

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/Django-6.0-green)](https://www.djangoproject.com/)
[![Playwright](https://img.shields.io/badge/Playwright-Enabled-blueviolet)](https://playwright.dev/)

An advanced LinkedIn AI Strategist SaaS platform built on top of Django. This project automates your entire professional brand strategy on LinkedIn: onboarding profile analysis, AI multi-model content generation, automated daily posting, strategic commenting, smart networking, lead client hunting, and automated job applications.

---

## 🌟 Key Features

1. **Intelligent Onboarding Wizard**
   - A multi-step flow to configure professional goals, target industries, credentials, and custom content themes.
   - Tailors an algorithmic LinkedIn growth strategy (e.g., *Thought Leader*, *Lead Generator*, *Job Hunter*, *Founders Brand*).

2. **Cost-Intelligent Multi-Model AI Router (`AIRouter`)**
   - Lazily loads and balances queries across various providers based on pricing tiers:
     - **Budget**: Groq (Llama 3) for high-speed, low-cost content.
     - **Balanced**: Gemini 1.5 Pro & OpenAI (GPT-4o) for balanced quality.
     - **Premium**: Anthropic (Claude 3.5 Sonnet) for peak copy and strategy.
   - Text generation outputs tailored LinkedIn posts, contextual comments, custom connection pitches, and bespoke cover letters.

3. **Graphic Post Visual Generator**
   - Automatically generates eye-catching, non-realistic abstract graphic canvases overlaying key quotes or ideas from the post.
   - Supports both programmatic Pillow-based designs and AI visual models (Stability AI, Replicate/Flux) to deliver visual depth.

4. **Playwright Automation Engine**
   - Robust browser automation scripts acting as a local background agent to perform human-like interactions:
     - **Posting Engine**: Safely logs in, navigates to LinkedIn, publishes scheduled updates with generated images.
     - **Contextual Commenter**: Searches for target industry topics and leaves thoughtful comments.
     - **Network Builder**: Targets connections in the selected niche and sends personalized invites.
     - **Job Applier**: Finds jobs matching keywords and applies with custom cover letters.
     - **Lead Hunter**: Searches for specific buyer personas and gathers client leads.

5. **Stripe Billing Integration**
   - Out-of-the-box billing app with Tier plans (Free, Pro, Elite) linked to Stripe Checkout and webhooks.

---

## 🛠️ Tech Stack

- **Framework**: Django 6.0, Django-Q2 (Background Task Queue)
- **Database**: SQLite (local dev) or PostgreSQL (production)
- **Styling**: Tailwind CSS
- **Automation**: Playwright (Headless Chromium)
- **AI Engine**: OpenAI API, Anthropic API, Google Generative AI API, Groq, Stability AI, Replicate
- **Graphics**: Pillow (PIL)

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10 or higher
- Node.js (for Tailwind builds)
- A Stripe account & API keys from AI providers (OpenAI, Anthropic, Gemini, Groq, Replicate, Stability AI)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/Teleiosite/LinkedIn-AI-Strategist.git
cd LinkedIn-AI-Strategist

# Install packages
pip install -r requirements.txt

# Install Playwright browser dependencies
playwright install chromium
```

### 3. Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```
Ensure you set the Django `SECRET_KEY`, `ENCRYPTION_KEY` (for securing LinkedIn credentials), and chosen AI provider keys.

### 4. Run Migrations & Setup
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 5. Start the Application
```bash
# Start background workers (Django-Q)
python manage.py qcluster

# Start development server
python manage.py runserver
```
Visit `http://127.0.0.1:8000` to onboard your strategist!

---

## 🤖 Running Background Automation Scripts
The scheduler run scripts are located in `linkedin/scripts/`. You can schedule them using the Django admin panel, Django-Q tasks, or standard cron jobs:

- **Daily Posting**: `python manage.py runscript post_publisher`
- **Strategic Commenting**: `python manage.py runscript commenter`
- **Network Growth**: `python manage.py runscript connection_builder`
- **Job Hunting & Application**: `python manage.py runscript job_applier`
- **Lead Generation / Prospecting**: `python manage.py runscript client_hunter`
- **Weekly Strategy Audit & Reports**: `python manage.py runscript weekly_reporter`

---

## 🔒 Security & Safe Automation
- We use Fernet symmetric encryption to store LinkedIn login credentials securely in the database.
- Playwright sessions simulate human-like pauses, variable scroll actions, and randomized timings to mimic authentic user behaviors.

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
