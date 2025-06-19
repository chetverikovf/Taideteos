      
import os
from dotenv import load_dotenv

load_dotenv()

# Генерируйте свой ключ командой в терминале: openssl rand -hex 32
SECRET_KEY = os.getenv("SECRET_KEY")
if SECRET_KEY is None:
    raise ValueError("The SECRET_KEY environment variable is not set. Please set it before running the application.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Время жизни токена
