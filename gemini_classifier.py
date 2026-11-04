import os
import re
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_MODEL = "gemini-3.5-flash-lite"


def classify_waste_image(image_bytes, mime_type=None):

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return {
            "success": False,
            "category": None,
            "explanation": "Gemini API key is missing.",
            "confidence": None
        }

    try:
        # Optimize uploaded image
        image = Image.open(BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((512, 512))

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=55)
        optimized_image = buffer.getvalue()

    except (UnidentifiedImageError, OSError, ValueError):
        return {
            "success": False,
            "category": None,
            "explanation": "Invalid or unsupported image.",
            "confidence": None
        }

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=120000)
        )

        prompt = """
Examine the uploaded image.

Describe the visible objects.
If biomedical waste is clearly identifiable,
suggest one category: Yellow, Red, White, or Blue.
Otherwise select Uncertain.

Return exactly these four lines:

Suggested Category: Uncertain
Visible Observation: Short description
Explanation: Short reason
Confidence: Low

Do not guess.
This is an AI suggestion only.
A qualified human reviewer must verify it.
"""

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=optimized_image,
                    mime_type="image/jpeg"
                )
            ],
            config=types.GenerateContentConfig(
                max_output_tokens=150,
                thinking_config=types.ThinkingConfig(
                    thinking_level="low"
                )
            )
        )

        result = response.text or ""

        print("GEMINI RAW RESPONSE:", repr(result))

        category_match = re.search(
            r"Suggested Category\s*:\s*(Yellow|Red|White|Blue|Uncertain)",
            result,
            re.IGNORECASE
        )

        confidence_match = re.search(
            r"Confidence\s*:\s*(Low|Medium|High)",
            result,
            re.IGNORECASE
        )

        category = (
            category_match.group(1).capitalize()
            if category_match else "Uncertain"
        )

        confidence = (
            confidence_match.group(1).capitalize()
            if confidence_match else "Not provided"
        )

        return {
            "success": True,
            "category": category,
            "explanation": result,
            "confidence": confidence
        }

    except Exception as error:

        print("ACTUAL GEMINI ERROR:", repr(error))

        return {
            "success": False,
            "category": None,
            "explanation": f"Gemini AI Error: {error}",
            "confidence": None
        }