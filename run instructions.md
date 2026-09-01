# Run Instructions

```bash
cd ~/Downloads

unzip -o SchoolMealAllergenSafetyMonitor_Local_All_Files.zip

cd SchoolMealAllergenSafetyMonitor_Local

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m py_compile app.py
python validate_project.py
python -m pytest -q

python -m streamlit run app.py --server.port 8501
```

Open `http://localhost:8501`.

If 8501 is busy:

```bash
pkill -f streamlit 2>/dev/null || true
python -m streamlit run app.py --server.port 8501
```

Or use:

```bash
python -m streamlit run app.py --server.port 8502
```
