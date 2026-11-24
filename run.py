import os
import sys
import subprocess
import uvicorn

bot = subprocess.Popen([sys.executable, "bot.py"])

try:
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000))
    )
finally:
    bot.terminate()
