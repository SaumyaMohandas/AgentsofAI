from flask import Flask, render_template, request
from dotenv import load_dotenv
import requests, os, re
import google.generativeai as genai

load_dotenv()
app = Flask(__name__)
#hi
GEMINI_API_KEY = os.getenv("GEMINI_API_KEYo")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def get_weather(location):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()
        if response.status_code != 200 or 'main' not in data:
            return None
        return f"{data['weather'][0]['description'].capitalize()}, {data['main']['temp']}\u00b0C, Humidity: {data['main']['humidity']}%"
    except:
        return None

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/old")
def old():
    return render_template('old.html')

@app.route("/submit", methods=["POST"])
def data():
    result_blocks = {
        "recommended": "",
        "advisory": "",
        "sustainable": "",
        "yield": "",
        "weather": "",
        "market": ""
    }

    location = request.form.get("location")
    crop = request.form.get("crop")
    soil = request.form.get("notes")

    if not soil:
        return render_template("output.html", error="Please describe your soil condition.")

    weather_report = get_weather(location) or "Unavailable"

    prompt = f"""
        You are an agricultural AI assistant.
        Based on the following:
        - Location: {location}
        - Soil condition: {soil}
        - Weather: {weather_report}
        {'- Planned Crop: ' + crop if crop else '- Recommend suitable crops'}

        Please provide structured outputs for the following 6 headings. Each section should only contain concise bullet points:

        === Recommended Crops ===
        === Crop Advisory ===
        === Sustainable Practices ===
        === Yield Improvement Tips ===
        === Weather Precautions ===
        === Market Trends ===
    """

    try:
        response = model.generate_content(prompt)
        text = response.text

        # Split sections
        sections = {
            "Recommended Crops": "",
            "Crop Advisory": "",
            "Sustainable Practices": "",
            "Yield Improvement Tips": "",
            "Weather Precautions": "",
            "Market Trends": ""
        }

        current_section = None
        for line in text.splitlines():
            if "Recommended Crops" in line:
                current_section = "Recommended Crops"
            elif "Crop Advisory" in line:
                current_section = "Crop Advisory"
            elif "Sustainable Practices" in line:
                current_section = "Sustainable Practices"
            elif "Yield Improvement Tips" in line:
                current_section = "Yield Improvement Tips"
            elif "Weather Precautions" in line:
                current_section = "Weather Precautions"
            elif "Market Trends" in line:
                current_section = "Market Trends"
            elif re.match(r"^[\-\•\*]", line.strip()) and current_section:
                line = re.sub(r"^[\-\•\*]\s*", "", line)                
                line = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", line)  # convert markdown bold to HTML bold
                sections[current_section] += f"<li style='text-align: left;'>{line}</li>"


        # Convert each to <ul>
        for key in sections:
            if sections[key]:
                sections[key] = f"<div><ul>{sections[key]}</ul></div>"


    except Exception as e:
        return render_template("output.html", result="<p class='text-danger'>❌ AI generation failed. Please try again.</p>")

    # OUTSIDE the try/except, after success
    return render_template(
        "output.html",
        location=location,
        weather=weather_report,
        recommended=sections["Recommended Crops"],
        advisory=sections["Crop Advisory"],
        sustainable=sections["Sustainable Practices"],
        yieldtips=sections["Yield Improvement Tips"],
        precautions=sections["Weather Precautions"],
        market=sections["Market Trends"]
    )



if __name__ == '__main__':
    app.run(debug=True)
