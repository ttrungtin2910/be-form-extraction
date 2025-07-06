import os

from dotenv import load_dotenv
load_dotenv()


class Configuration():
    # Open AI
    OPENAI_KEY = os.getenv("OPENAI_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL")
    OPENAI_TEMPERATURE = os.getenv("OPENAI_TEMPERATURE")

    # Google cloud
    PROJECT_ID = os.getenv("PROJECT_ID")
    LOCATION = os.getenv("LOCATION")
    PROCESSOR_ID = os.getenv("PROCESSOR_ID")
    PROCESSOR_VERSION_ID = os.getenv("PROCESSOR_VERSION_ID")
    GOOGLE_APPLICATION_CREDENTIALS= os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
