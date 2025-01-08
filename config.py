from dotenv import find_dotenv, load_dotenv
import os

if find_dotenv():
    load_dotenv()

VK_API_KEY = os.getenv("VK_API_KEY")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH_TO_PYTHON = os.path.normpath(os.path.join(BASE_DIR, "venv/Scripts/python.exe"))

