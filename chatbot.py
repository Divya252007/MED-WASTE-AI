import os
from io import BytesIO

import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_MODEL = "gemini-3.5-flash-lite"


# =====================================================
# GEMINI API KEY
# =====================================================

def get_api_key():

    try:
        key = st.secrets.get("GEMINI_API_KEY")
        if key:
            return key
    except Exception:
        pass

    return os.getenv("GEMINI_API_KEY")


# =====================================================
# BIOMEDICAL WASTE KNOWLEDGE INSTRUCTIONS
# =====================================================

SYSTEM_PROMPT = """
You are MED WASTE AI, a biomedical waste segregation
and management assistant for healthcare staff in India.

Your purpose is to help Nurses and Doctors understand
biomedical waste categories and safe segregation.

Follow India's Bio-Medical Waste Management Rules, 2016,
including applicable amendments and CPCB guidance.

FOUR COLOUR CATEGORIES:

1. YELLOW:
Human and animal anatomical waste, soiled waste such as
blood/body-fluid contaminated dressings and cotton swabs,
discarded medicines, specified chemical waste, and
specified laboratory waste.

2. RED:
Contaminated recyclable plastic waste such as tubing,
IV sets, catheters, urine bags, gloves and eligible
plastic items. Sharps must not be placed here.

3. WHITE (TRANSLUCENT):
Waste sharps including needles, blades, scalpels and
other contaminated sharp metal objects. Use the
specified puncture-proof, leak-proof and tamper-proof
container.

4. BLUE:
Specified contaminated glassware such as medicine vials
and ampoules (subject to applicable exceptions), and
metallic body implants. Use the specified blue-marked
container.

IMPORTANT CLASSIFICATION RULES:

- Blood-soaked cotton, dressings and similar soiled
  materials generally belong to Yellow.
- A contaminated needle or blade belongs to White,
  not Yellow or Red.
- Contaminated recyclable plastic belongs to Red.
- Do not classify an item only by its colour or appearance.
- Consider the material, contamination and whether it
  is a sharp.
- Ordinary non-biomedical waste must not be forced into
  one of the four biomedical categories.
- If information is insufficient, ask a short clarifying
  question instead of guessing.
- An image cannot always reveal contamination or material
  composition. Explain this limitation.

FOR EACH QUESTION, EXPLAIN:

1. Recommended colour category.
2. Reason for classification.
3. How to segregate it at the point where it is generated.
4. General treatment and authorised disposal route.
5. Possible risks of incorrect segregation or disposal.

DISPOSAL SAFETY:

- Explain the applicable treatment route at a general level.
- Direct healthcare facilities to their authorised
  Common Biomedical Waste Treatment Facility (CBWTF)
  and approved hospital SOP.
- Do not tell users to burn, dump, mix, or personally
  treat biomedical waste.
- Do not recommend manual sorting of mixed waste.
- Never advise unsafe handling of sharps.
- Do not invent exact treatment parameters or local rules.

RESPONSE STYLE:

- Use simple English or Tamil according to the selected
  language.
- Use clear headings and short bullet points.
- Be practical and easy for Nurses and Doctors to understand.
- Do not claim that your answer is a final medical or
  regulatory approval.
- A qualified human reviewer must make the final decision.
"""


# =====================================================
# IMAGE OPTIMIZATION
# =====================================================

def prepare_image(image_bytes):

    try:
        image = Image.open(BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((768, 768))

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=75)

        return buffer.getvalue()

    except (UnidentifiedImageError, OSError, ValueError):
        return None


# =====================================================
# GEMINI CHAT RESPONSE
# =====================================================

def get_chatbot_response(question, history, image_bytes=None,
                         language="English"):

    api_key = get_api_key()

    if not api_key:
        return (
            "Gemini API key is missing. Please configure "
            "GEMINI_API_KEY in your environment or Streamlit Secrets."
        )

    try:

        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=120000)
        )

        conversation = ""

        for item in history[-8:]:

            role = item["role"].upper()
            conversation += (
                f"\n{role}: {item['text']}\n"
            )

        prompt = f"""
{SYSTEM_PROMPT}

RESPONSE LANGUAGE: {language}

PREVIOUS CONVERSATION:
{conversation}

CURRENT USER QUESTION:
{question}

If an image is attached, examine visible objects carefully.
Do not claim that invisible contamination is confirmed.

Give the recommended category only when sufficient
information is available. Otherwise ask for clarification.

Clearly separate general guidance from final human approval.
"""

        contents = [prompt]

        if image_bytes:

            optimized_image = prepare_image(image_bytes)

            if optimized_image is None:
                return "The uploaded image is invalid. Please upload a clear JPG or PNG image."

            contents.append(
                types.Part.from_bytes(
                    data=optimized_image,
                    mime_type="image/jpeg"
                )
            )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=900
            )
        )

        answer = response.text

        if not answer:
            return "I could not generate an answer. Please try again."

        return answer

    except Exception as error:

        print("MED WASTE CHATBOT ERROR:", repr(error))

        return (
            "Sorry, the AI assistant is temporarily unavailable. "
            "Please try again later. You can still use the normal "
            "waste registration and Doctor verification features."
        )


# =====================================================
# CHATBOT PAGE
# =====================================================

def chatbot_page(user):

    st.title("🤖 MED WASTE AI Assistant")

    st.caption(
        "Ask about biomedical waste categories, segregation, "
        "disposal procedures and safety."
    )

    user_id = user.get("user_id", user.get("username", "user"))

    chat_key = f"waste_ai_chat_{user_id}"

    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    history = st.session_state[chat_key]

    # Language selection
    language = st.selectbox(
        "Response Language",
        ["English", "Tamil"],
        key=f"assistant_language_{user_id}"
    )

    st.divider()

    st.markdown("### 💬 Ask your waste management question")

    # Display previous messages
    for message in history:

        with st.chat_message(message["role"]):

            st.markdown(message["text"])

            if message.get("image_bytes"):
                st.image(
                    message["image_bytes"],
                    width=250
                )

    # Input form
    with st.form(
        key=f"assistant_form_{user_id}",
        clear_on_submit=True
    ):

        question = st.text_area(
            "Describe the waste or enter your question",
            placeholder=(
                "Example: Blood-soaked cotton. "
                "Which colour category should I use?"
            ),
            height=100
        )

        uploaded_file = st.file_uploader(
            "Or upload a waste image",
            type=["jpg", "jpeg", "png"]
        )

        submitted = st.form_submit_button(
            "✨ Ask MED WASTE AI",
            use_container_width=True
        )

    if submitted:

        if not question.strip() and uploaded_file is None:

            st.warning(
                "Please enter a question or upload an image."
            )

        else:

            image_bytes = (
                uploaded_file.getvalue()
                if uploaded_file else None
            )

            display_question = question.strip()

            if not display_question:
                display_question = (
                    "Please examine this uploaded waste image "
                    "and provide a cautious classification."
                )

            user_message = {
                "role": "user",
                "text": display_question,
                "image_bytes": image_bytes
            }

            history.append(user_message)

            with st.spinner(
                "MED WASTE AI is analysing your question..."
            ):

                answer = get_chatbot_response(
                    display_question,
                    history[:-1],
                    image_bytes,
                    language
                )

            history.append({
                "role": "assistant",
                "text": answer,
                "image_bytes": None
            })

            st.rerun()

    st.divider()

    if st.button(
        "🗑️ Clear Chat",
        key=f"clear_assistant_{user_id}"
    ):

        st.session_state[chat_key] = []
        st.rerun()

    st.info(
        "AI guidance is advisory only. Follow your hospital's "
        "approved SOP and applicable biomedical waste rules. "
        "The Doctor or authorised human reviewer makes the "
        "final verification decision."
    )