import base64
import json
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# from pydantic.v1 import SecretStr  # Not needed for newer langchain versions
from properties.prompts import PROMPT_SAMPLES
from properties.config import Configuration


class TicketChatBot:
    def __init__(self, config: Configuration):
        self.config = config

        # Validate required configuration values
        if not self.config.OPENAI_MODEL:
            raise ValueError("OPENAI_MODEL is required")
        if not self.config.OPENAI_TEMPERATURE:
            raise ValueError("OPENAI_TEMPERATURE is required")
        if not self.config.OPENAI_KEY:
            raise ValueError("OPENAI_KEY is required")

        self.llm = ChatOpenAI(
            model=self.config.OPENAI_MODEL,
            temperature=float(self.config.OPENAI_TEMPERATURE),
            api_key=self.config.OPENAI_KEY,
        )
        self.prompt_config = PROMPT_SAMPLES["ticket_information"]

    def encode_image_base64(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def build_messages(self, ocr_text: str, image_base64: str) -> list:
        system_prompt = self.prompt_config["system_prompt"]
        user_prompt = self.prompt_config["user_prompt"].format(context=ocr_text)

        return [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=[
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    },
                ]
            ),
        ]

    async def analyze_ticket(self, image_path: str, ocr_text: str) -> dict:
        image_base64 = self.encode_image_base64(image_path)
        messages = self.build_messages(ocr_text, image_base64)
        response = await self.llm.ainvoke(messages)
        # Handle both string and list response content
        content = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )
        return self.post_processing(content)

    def analyze_ticket_sync(self, image_path: str, ocr_text: str) -> dict:
        # New synchronous helper for Celery tasks
        image_base64 = self.encode_image_base64(image_path)
        messages = self.build_messages(ocr_text, image_base64)
        response = self.llm.invoke(messages)
        content = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )
        return self.post_processing(content)

    def post_processing(self, content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print("❌ JSON parsing error:", e)
            return {"error": "Invalid JSON format", "raw_response": content}
