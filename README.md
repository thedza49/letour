# LeTour Fantasy

Tour de France Fantasy League

## How to run on your server

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
