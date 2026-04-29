import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SAM_API_KEY = os.getenv("SAM_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


settings = Settings()