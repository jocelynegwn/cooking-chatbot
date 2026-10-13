import streamlit as st
import requests
import time
from google import genai

try:
    google_api_key = st.secrets["GEMINI"]
except Exception:
    google_api_key = None

if not google_api_key:
    st.error("API Key is missing!")
    st.stop()

# CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.55), rgba(0, 0, 0, 0.7)), 
                    url('https://images.unsplash.com/photo-1507089947368-19c1da9775ae?q=80&w=1920&auto=format&fit=crop') !important;
        background-size: cover !important;
        background-position: center center !important;
        background-attachment: fixed !important;
        color: #f5f5f5 !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: rgba(20, 20, 20, 0.92) !important;
        border-right: 1px solid rgba(255, 215, 0, 0.2);
    }
    
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #ffffff !important;
        text-shadow: none !important;
    }

    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        color: #000000 !important;
        background-color: #ffffff !important;
    }

    div[data-testid="stChatInput"] textarea {
        color: #000000 !important;
        background-color: #ffffff !important;
        -webkit-text-fill-color: #000000 !important;
        padding: 12px 15px !important;
        font-size: 16px !important;
    }
    
    .stChatInputContainer textarea::placeholder {
        color: #666666 !important;
        -webkit-text-fill-color: #666666 !important;
    }

    .stChatMessage button, .stChatMessage div[data-testid="stButton"] button {
        color: #000000 !important;
        font-weight: 600 !important;
        background-color: #f8f9fa !important;
        border: 1px solid #cccccc !important;
    }
    .stChatMessage button:hover, .stChatMessage div[data-testid="stButton"] button:hover {
        background-color: #e2e6ea !important;
        color: #000000 !important;
    }

    .stChatMessage {
        background-color: rgba(20, 20, 20, 0.9) !important;
        border: 1px solid rgba(255, 215, 0, 0.3) !important;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        color: #ffffff !important;
    }
    
    .stChatMessage p, .stChatMessage li, .stChatMessage span {
        color: #ffffff !important;
    }

    h1, h2, h3 {
        color: #ffdd99 !important;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.8);
        font-weight: 700;
    }
    p, .stCaption, label {
        color: #e0e0e0 !important;
        font-weight: 500;
        text-shadow: 0 1px 4px rgba(0, 0, 0, 0.8);
    }
</style>
""", unsafe_allow_html=True)

if "genai_client" not in st.session_state:
    st.session_state.genai_client = genai.Client(api_key=google_api_key)

if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "allergy": "",
        "disliked": "",
        "liked": "",
        "favorite_ingredient": "",
        "diet": "None",
        "other_notes": ""
    }

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
st.sidebar.title("🍳 Navigation Menu")
nav_choice = st.sidebar.radio("Select Page:", ["💬 Chat Assistant", "👤 My Profile & Preferences"])

if nav_choice == "👤 My Profile & Preferences":
    st.sidebar.markdown("---")
    st.sidebar.subheader("Profile & Diet Settings")
    
    with st.form("profile_form"):
        allergy = st.text_input("Food allergies:", value=st.session_state.user_profile["allergy"], placeholder="e.g., Nuts, Seafood")
        disliked = st.text_input("Disliked foods / ingredients:", value=st.session_state.user_profile["disliked"], placeholder="e.g., Garlic, Onion")
        liked = st.text_input("Favorite foods:", value=st.session_state.user_profile["liked"], placeholder="e.g., Ramen, Fried Chicken")
        favorite_ingredient = st.text_input("Favorite ingredients:", value=st.session_state.user_profile["favorite_ingredient"], placeholder="e.g., Cheese, Beef, Mushrooms")
        diet = st.selectbox("Current diet status:", ["None", "Keto Diet", "Vegan Diet", "Low Calorie Diet", "Vegetarian", "Others"], index=["None", "Keto Diet", "Vegan Diet", "Low Calorie Diet", "Vegetarian", "Others"].index(st.session_state.user_profile["diet"]) if st.session_state.user_profile["diet"] in ["None", "Keto Diet", "Vegan Diet", "Low Calorie Diet", "Vegetarian", "Others"] else 0)
        other_notes = st.text_area("Other notes or food preferences:", value=st.session_state.user_profile["other_notes"], placeholder="e.g., Prefer spicy food, avoid heavy late-night dinners.")
        
        submitted = st.form_submit_button("💾 Save Profile")
        if submitted:
            st.session_state.user_profile = {
                "allergy": allergy,
                "disliked": disliked,
                "liked": liked,
                "favorite_ingredient": favorite_ingredient,
                "diet": diet,
                "other_notes": other_notes
            }
            st.session_state.pop("chat", None)
            st.success("Profile saved successfully! Chef AI has memorized your preferences.")

p = st.session_state.user_profile
system_instruction = f"""
You are Chef AI, a professional, friendly, and creative cooking assistant. 
Your role is to help users find recipes, give cooking tips, suggest menu substitutions, and guide them step-by-step in the kitchen.

--- USER PROFILE & PREFERENCES (MEMORY) ---
- Food Allergies: {p['allergy'] if p['allergy'] else 'No allergies reported'}
- Disliked Foods / Ingredients to Avoid: {p['disliked'] if p['disliked'] else 'None'}
- Favorite Foods: {p['liked'] if p['liked'] else 'None specific'}
- Favorite Ingredients: {p['favorite_ingredient'] if p['favorite_ingredient'] else 'Any'}
- Diet Status: {p['diet']}
- Other Notes: {p['other_notes'] if p['other_notes'] else 'None'}

MAIN RULES:
1. STRICTLY FOLLOW THE PROFILE! NEVER include or recommend recipes containing allergens or foods/ingredients the user dislikes (items listed under 'Food Allergies' and 'Disliked Foods / Ingredients to Avoid'). If a traditional recipe normally contains any of these restricted items, you MUST explicitly modify the recipe to exclude them or suggest safe substitutions.
2. Tailor recipe recommendations to match their diet status and favorite foods.
3. Use a friendly, warm, and encouraging tone in English.
"""

def init_chat():
    return st.session_state.genai_client.chats.create(
        model="gemini-3.8-flash",
        config={
            "system_instruction": system_instruction,
            "temperature": 0.5
        }
    )

if "chat" not in st.session_state:
    st.session_state.chat = init_chat()

def send_message_with_retry(chat_session, prompt, retries=3, delay=2):
    for attempt in range(retries):
        try:
            response = chat_session.send_message(prompt)
            return response.text if hasattr(response, "text") else str(response)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                st.session_state.chat = init_chat()
                try:
                    response = st.session_state.chat.send_message(prompt)
                    return response.text if hasattr(response, "text") else str(response)
                except Exception as err:
                    return f"Sorry, the server is busy right now. Please try again in a moment. (Error: {err})"

if nav_choice == "💬 Chat Assistant":
    st.title("🍳 Chef AI: Cooking Assistant & Recipes")
    st.caption("Ask for recipes, find meal inspiration, or get cooking tips tailored to your profile!")

    def handle_preset_click(preset_prompt):
        st.session_state.messages.append({"role": "user", "content": preset_prompt})
        answer = send_message_with_retry(st.session_state.chat, preset_prompt)
        st.session_state.messages.append({"role": "assistant", "content": answer})

    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            if msg["role"] == "assistant" and idx == len(st.session_state.messages) - 1:
                st.write("")
                cols = st.columns([1.1, 1.3, 1.2, 1.4])
                with cols[0]:
                    if st.button("🔄 New Recipe", key=f"reset_{idx}"):
                        st.session_state.pop("chat", None)
                        st.session_state.pop("messages", None)
                        st.rerun()
                with cols[1]:
                    if st.button("🍗 Chicken Menu", key=f"chick_{idx}"):
                        handle_preset_click("Please provide a delicious chicken dish recipe. Strictly ensure it contains ZERO allergens or any ingredients listed in my disliked profile.")
                        st.rerun()
                with cols[2]:
                    if st.button("🍝 Pasta Menu", key=f"pasta_{idx}"):
                        handle_preset_click("Give me a special pasta recipe that fits my dietary preferences and strictly excludes any allergens or disliked ingredients from my profile.")
                        st.rerun()
                with cols[3]:
                    if st.button("💡 Menu Suggestion", key=f"rec_{idx}"):
                        handle_preset_click("Based on my profile, allergies, and favorite foods, what is the best dish for me to cook today?")
                        st.rerun()

    prompt = st.chat_input("Ask for a recipe or request meal suggestions based on your profile...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        answer = send_message_with_retry(st.session_state.chat, prompt)

        with st.chat_message("assistant"):
            st.markdown(answer)
            
            st.write("")
            cols = st.columns([1.1, 1.3, 1.2, 1.4])
            with cols[0]:
                if st.button("🔄 New Recipe", key="reset_new"):
                    st.session_state.pop("chat", None)
                    st.session_state.pop("messages", None)
                    st.rerun()
            with cols[1]:
                if st.button("🍗 Chicken", key=f"chick_new"):
                    handle_preset_click("Please provide a delicious chicken dish recipe. Strictly ensure it contains ZERO allergens or any ingredients listed in my disliked profile.")
                    st.rerun()
            with cols[2]:
                if st.button("🍝 Pasta Menu", key=f"pasta_new"):
                    handle_preset_click("Give me a special pasta recipe that fits my dietary preferences and strictly excludes any allergens or disliked ingredients from my profile.")
                    st.rerun()
            with cols[3]:
                if st.button("💡 Menu Suggestion", key=f"rec_new"):
                    handle_preset_click("Based on my profile, allergies, and favorite foods, what is the best dish for me to cook today?")
                    st.rerun()

        st.session_state.messages.append({"role": "assistant", "content": answer})
