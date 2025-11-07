# import openai
import assemblyai as aai
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template

load_dotenv()
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

aai.settings.api_key = ASSEMBLYAI_API_KEY

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generateimages/<prompt>")
def generate(prompt):
    print("prompt:", prompt)
    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    print(response)
    return jsonify(response)



