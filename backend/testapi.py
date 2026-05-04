import google.generativeai as genai

# 🔑 Replace this with your API key
API_KEY = "AIzaSyC6kgYJahXdJQ2LEFvQu2KP-cHGpz-4HPQ"

genai.configure(api_key=API_KEY)

def test_gemini():
    try:
        # List available models (important debug step)
        print("🔍 Fetching available models...\n")
        models = genai.list_models()

        for m in models:
            print("✔", m.name)

        print("\n🧠 Testing generation...\n")

        # Try a simple prompt
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content("Say hello in one sentence")

        print("✅ SUCCESS RESPONSE:")
        print(response.text)

    except Exception as e:
        print("\n❌ ERROR OCCURRED:")
        print(e)

if __name__ == "__main__":
    test_gemini()