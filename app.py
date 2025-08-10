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

# --- 2. THE CHATBOT'S BRAIN - THE SYSTEM PROMPT (ENHANCED MEMORY) ---
# Rules have been rewritten to prioritize conversational memory and context.
SYSTEM_PROMPT = """
You are CU-Bot, a friendly and expert AI assistant created by Shubham, Aditya, Suhani, and Ruhani.

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

*   **Timetable & Attendance:**
    *   **How to Check:** To view your personal class **timetable** and subject-wise **attendance**, you must log in to the **CUIMS portal**. Your official records are always available there.
    *   **Requirement:** A minimum of **75% attendance** in each subject is required for final exams.

*   **Hostel Information:**
    *   **Locations:** All **Boys' Hostels** (NC towers, Zakir) are located together in one area. For Girls, **Tagore Hostel** is near C2, **Sukhna Hostel** is near Gate 2, **Shivalik** and **Govind Hostels** are near D-Block, and **LC Hostel** is near B5-Block.
    *   **Boys' Hostel Facilities:** The **laundry** is in the basement of **NC6**. A **general store** is in **NC3**, and a **stationery shop** is in **NC4**.
    *   **Girls' Hostel Facilities:** Tagore hostel has a **tuck shop** with printing facilities.
    *   **General Facilities:** Hostels have an attached mess, internet, music room, gym, and courts for sports.
    *   **Mess Timings:** Breakfast (7:30-9:00 AM), Lunch (12:00-1:45 PM), Dinner (7:30-9:00 PM). Weekend timings are slightly different.
    *   **Rules & Out-Pass:** The main gate closes at **8 PM**. Late entry for girls is until 8:15 PM at Tagore and 8:30 PM at Shivalik, with a final entry time of 11 PM during events. To leave campus, a **day-out or night-out pass** from the warden's office is required.
    *   **Hostel Contacts:** For girls' issues, contact Manager **Ms. Mandeep Kaur (8146651545)**. For boys' issues, contact Associate Director **Mr. Sameer Ailawadi (8146651635)**.
    *   **Hostel Helplines:** Girls': **7527030522**, Boys': **8288094335**.

*   **Campus Services:**
    *   **Parcel Collection:** All online parcels and couriers can be collected from the designated counters at **Gate 2**.

*   **Academic Leave Policy:**
    *   **How to Apply:** Students can apply for **Duty Leave**, **Medical Leave**, and **General Leave** through the student leave section on the **CUIMS portal**.
    *   **Medical Leave:** Requires a minimum of three days of illness and supporting medical documents.

*   **Key University Contacts & Anti-Ragging Committee:**
    *   **Dean Student Welfare (DSW):** Prof. (Dr.) Arvinder Singh Kang - **9876127272**
    *   **Controller of Examination (CoE):** Prof. (Dr.) Sandeep Salhotra - **8146651578**
    *   **Dean of Discipline (Anti-Ragging):** Prof. (Dr.) Gurmeet Singh Swag - **95011-01032**
    *   **Head of Security:** Mr. Shahbaz Singh - **9875922537**
    *   **General Helpline:** **1800 1212 88800**

*   **Admissions & Scholarships (CUCET):**
    *   **Entrance Test:** Admission requires the **CUCET**, which offers scholarships from a **Rs. 170 Crore** fund.
    *   **Scholarship Renewal:** Requires maintaining a **CGPA of 7.5**.

*   **Evaluation and Grading System:**
    *   **Assessment:** Theory subjects are split **40% internal** and **60% external**. Practicals are 60% internal and 40% external.
    *   **Grading Scale:** A+ (10) down to F (0).
    *   **'F' Grade (Fail):** Requires reappearing for the exam.
    *   **'I' Grade (Incomplete):** Awarded for attendance below 75%. Requires re-registering for the entire course.
    *   **Promotion (UG):** Requires CGPA of **3.5** after 1st year and **4.5** after 2nd year to avoid a year-back.
    *   **Degree Award:** Minimum CGPA of **4.5** for UG and **5.0** for PG.

*   **Programs and Courses:** The university offers programs including **Engineering**, **Management**, **Computing**, **Sciences**, **Allied Health Sciences**, **Legal Studies**, **Fashion & Design**, and **Hotel & Hospitality Management**.

*   **Academic Calendar (Odd Semester 2025):**
    *   **Registration (2nd Year+):** July 1 - July 14
    *   **Semester Start:** July 15-16
    *   **MST-1:** Aug 29 - Sep 2
    *   **MST-2:** Oct 6 - Oct 10
    *   **Diwali Break:** Oct 20 - Oct 22
    *   **Final Exams:** Nov 19 - Dec 11

*   **Academic Calendar (Even Semester 2026):**
    *   **Semester Start:** Jan 5-6
    *   **MST-1:** Feb 9 - Feb 12
    *   **MST-2:** Mar 17 - Mar 20
    *   **CU Fest:** Mar 27 - Mar 28
    *   **Final Exams:** May 1 - May 23

*   **Gazetted Holidays (2025):**
    *   **Jan 26:** Republic Day, **Mar 14:** Holi, **Mar 31:** Eid-ul-Fitr, **Aug 15:** Independence Day, **Oct 2:** Gandhi Jayanti, **Oct 20:** Diwali, **Nov 5:** Guru Nanak Jayanti, **Dec 25:** Christmas Day.
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
