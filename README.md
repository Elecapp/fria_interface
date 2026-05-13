# FRIA Support System (UX/UI Fork)
This repository is a fork of the original FRIA (Fairness and Rights in AI) Support System. 

The goal of this fork is to redesign and improve the User Experience (UX) and User Interface (UI) of the platform. The new design aims to make the process of evaluating AI models for fairness, non-discrimination, and privacy more accessible, intuitive, and visually coherent for different types of users (Experts, Non-experts, Technical Auditors).

## Prerequisites
Ensure you have met the following requirements:
* **Node.js** (v16 or higher) and **npm** installed.
* **Python** (3.9 or higher) installed.

## How to Run the Project (Local Development)
To start the system, you need to run both the Backend server and the Frontend development server in two separate terminal windows.

### 1. Start the Backend (FastAPI / Python)

Open your first terminal, navigate to the root folder of the project, and follow these steps:

```bash
# Create a virtual environment (highly recommended)
python -m venv venv

# Activate the virtual environment

# Install the required Python dependencies
pip install -r requirements.txt

# Start the FastAPI server (runs by default on port 8000)
uvicorn backend.main:app --reload --port 8000
```
### 2. Start the Frontend (Vue.js / Vite)

# Navigate to the frontend directory
cd frontend
```bash
# Install Node dependencies (only needed the first time)
npm install

# Start the development server
npm run dev
```
