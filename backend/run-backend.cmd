@echo off
cd /d "C:\Zappizo AI\ERP_Builder_emergent\backend"
"C:\Users\rbisw\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn server:app --host 127.0.0.1 --port 8001
