#!/bin/bash
cd /Users/saminyasar/Documents/augment-projects/SalesTrack/backend
exec /usr/bin/python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
