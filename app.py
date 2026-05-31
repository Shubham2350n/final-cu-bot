import os
import requests
from flask import Flask, request, jsonify, render_template, session
from openai import OpenAI 

# --- 1. INITIALIZATION ---
app = Flask(__name__)
app.secret_key = os.urandom(24) 

# --- Get all the secret keys from Render's environment ---
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID")

# --- Initialize the AI client ---
client = None
if OPENROUTER_API_KEY:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )
    print("OpenRouter client initialized successfully.")
else:
    print("WARNING: OpenRouter API Key is not set.")

# --- 2. THE CHATBOT'S BRAIN - THE SYSTEM PROMPT (FINAL VERSION) ---
# Combines the conversational memory fix with the direct demo responses.
SYSTEM_PROMPT = """
You are CU-Bot, a friendly and expert AI assistant created by khushi kumari.

**Core Rules (Follow Strictly):**
1.  **Maintain Conversational Context (CRITICAL):** Your most important job is to have a natural, flowing conversation. You MUST use the entire chat history to understand context, pronouns (like 'it', 'they'), and follow-up questions. If a user asks "what about for girls?", you must look at the previous turn to understand what topic they are asking about.
2.  **Greeting vs. Factual Query:**
    *   If the user's input is ONLY a greeting (like "hi" or "hello"), reply with ONLY the phrase: "Hello! How can I assist you?".
    *   Do NOT add a greeting if the user is asking a question. Answer the question directly.
3.  **Direct and Brief Answers:** Get straight to the point. Keep answers to 2-3 sentences unless providing a list.
4.  **Use Your Knowledge:** Answer all questions using the detailed knowledge base below.

**Your Knowledge Base (Private):**

*   **Hackathon Demo - Image-based Directions:**
    *   **User Trigger Phrase:** "Find the best direction to Hostel from the location in the image."
    *   **Your Pre-defined Response:** "Of course! From the main entrance, go left in the direction of Tagore Hostel. You will see a road on your right, next to a parking field. Follow that road and you will see underground stairs. That path leads directly to the boys' hostel gate."

*   **Attendance Information (Demo):**
    *   **If a user asks about "attendance",** provide this exact sample record: "Of course, here is your attendance record:
        - ADVANCED DATA STRUCTURES: **85%**
        - Object Oriented Programming using JAVA: **100%**
        - OPERATING SYSTEM: **100%**
        - Agile Development Methodologies: **94.12%**"

*   **Timetable Information (Demo):**
    *   **If a user asks about their "timetable" or "schedule",** provide this exact sample schedule: "Certainly! Here is your class schedule:
        - **Monday:** 10:20 AM: OPERATING SYSTEM
        - **Tuesday:** 9:30 AM: Probability and Statistics
        - **Wednesday:** 9:30 AM: OPERATING SYSTEM
        - **Thursday:** 9:30 AM: ADVANCED DATA STRUCTURES
        - **Friday:** 1:55 PM: Object Oriented Programming"

*   **Hostel Information:**
    *   **Locations:** All **Boys' Hostels** (NC towers, Zakir) are located together in one area. For Girls, **Tagore Hostel** is near C2, **Sukhna Hostel** is near Gate 2, **Shivalik** and **Govind Hostels** are near D-Block, and **LC Hostel** is near B5-Block.
    *   **Rules & Out-Pass:** The main gate closes at **8 PM**. Late entry for girls is until 8:15 PM at Tagore and 8:30 PM at Shivalik. A **day-out or night-out pass** is required.
    *   **Mess Timings:** Breakfast (7:30-9:00 AM), Lunch (12:00-1:45 PM), Dinner (7:30-9:00 PM).
    *   **Hostel Helplines:** Girls': **7527030522**, Boys': **8288094335**.

*   **Campus Services:**
    *   **Parcel Collection:** All parcels can be collected from the counters at **Gate 2**.

*   **Academic Leave Policy:**
    *   **How to Apply:** Apply for **Duty, Medical, or General Leave** via the **CUIMS portal**.

*   **Key University Contacts & Anti-Ragging Committee:**
    *   **DSW:** Prof. (Dr.) Arvinder Singh Kang - **9876127272**
    *   **CoE:** Prof. (Dr.) Sandeep Salhotra - **8146651578**
    *   **Dean of Discipline (Anti-Ragging):** Prof. (Dr.) Gurmeet Singh Swag - **95011-01032**

*   **Admissions & Scholarships (CUCET):**
    *   **Entrance Test & Renewal:** Admission requires the **CUCET**. To renew a scholarship, maintain a **CGPA of 7.5**.

*   **Evaluation and Grading System:**
    *   **Assessment:** Theory subjects are **40% internal** and **60% external**.
    *   **'I' Grade (Incomplete):** Awarded for attendance below 75%, requiring course re-registration.
    *   **Promotion & Degree:** Requires CGPA of **3.5** after 1st year and **4.5** after 2nd year. Minimum CGPA of **4.5** for a UG degree.
"""

# --- 3. HELPER FUNCTIONS ---
def should_perform_search(query):
    query = query.lower().strip()
    greetings = ["hi", "hello", "hey", "hii", "heyy"]
    if query in greetings: return False
    
    cu_keywords = [
        "cu", "cuchd", "chandigarh university", "hostel", "cuims", "dsw", 
        "holiday", "exam", "test", "mst", "semester", "registration",
        "fest", "calendar", "diwali", "holi", "grading", "cgpa", "sgpa",
        "course", "program", "admission", "cucet", "scholarship", "laundry", 
        "store", "stationery", "nc6", "tagore", "shivalik", "sukhna", "tuck shop", 
        "out pass", "gate", "contact", "helpline", "security", "discipline", 
        "ragging", "coe", "dean", "leave", "attendance", "parcel", "delivery", 
        "timetable", "schedule", "directions", "mess timing", "canteen",
        "direction", "location", "image"
    ]
    if any(keyword in query for keyword in cu_keywords): return False
    return True

def google_search(query):
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID: return ""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {'key': GOOGLE_API_KEY, 'cx': GOOGLE_CSE_ID, 'q': query, 'num': 3}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        snippets = [item.get('snippet', '') for item in response.json().get('items', [])]
        return f"Web search results for context:\n---BEGIN---\n{' '.join(snippets)}\n---END---"
    except Exception as e:
        print(f"An error during Google search: {e}")
        return ""

# --- 4. API LOGIC WITH CONVERSATION MEMORY ---
@app.route('/')
def home():
    # Clear the history for a new conversation session
    session.pop('chat_history', None)
    return render_template('index.html') 

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message: return jsonify({"response": "Please enter a message."})
    if not client: return jsonify({"response": "Chatbot is not configured."})

    # Retrieve chat history from the session, or start a new one
    chat_history = session.get('chat_history', [])
    if not chat_history:
        chat_history.append({"role": "system", "content": SYSTEM_PROMPT})

    # Add the new user message to the history
    chat_history.append({"role": "user", "content": user_message})
    
    current_prompt = list(chat_history)
    
    # Perform a Google search for general knowledge questions
    if should_perform_search(user_message):
        search_context = google_search(user_message)
        if search_context:
            current_prompt.insert(-1, {"role": "system", "content": search_context})

    try:
        response = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct:free",
            messages=current_prompt,
            temperature=0.6,
        )
        ai_response = response.choices[0].message.content
        
        # Add the AI's response to the history
        chat_history.append({"role": "assistant", "content": ai_response})
        
        # Save the updated history back to the session
        session['chat_history'] = chat_history
        
        return jsonify({"response": ai_response})
    except Exception as e:
        print(f"An error with OpenRouter API: {e}")
        return jsonify({"response": "I'm having a bit of trouble connecting right now. Please try again."})

if __name__ == '__main__':
    app.run(debug=True)
