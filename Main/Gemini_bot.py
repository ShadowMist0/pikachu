from google import genai
client = genai.Client(api_key="AIzaSyDWdLcZ0tv8Sns3JAcTZ3YvTzgzOhgzKj0")
response = client.models.generate_content(
    model = "gemini-2.0-flash",
    contents = "hi, respond in one word.",
)
print(response.text)


gemini-2.5-flash-preview-native-audio-dialog &
gemini-2.5-flash-exp-native-audio-thinking-dialog


