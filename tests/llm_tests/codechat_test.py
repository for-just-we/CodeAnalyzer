import sys
import google.generativeai as genai
from google.generativeai.text import Completion
from google.generativeai.discuss import ChatResponse

# currently the default temperature of gemini is 0.4
def list_models():
    for m in genai.list_models():
        # if 'generateContent' in m.supported_generation_methods:
        print(m)
        print(m.name)


def test_icall_text_decl():
    from ..test_data import context
    response: Completion = genai.generate_text(
        model='models/text-bison-001', prompt=context, temperature=0.8, max_output_tokens=1024)
    print(response.result)


def test_icall_chat_decl():
    from ..test_data import context
    chat: ChatResponse = genai.chat(model="models/chat-bison-001", messages=[context], temperature=0.8)
    print(chat.last)


if __name__ == '__main__':
    api_key = sys.argv[1]
    genai.configure(api_key=api_key)
    list_models()

    print("==================")
    test_icall_chat_decl()