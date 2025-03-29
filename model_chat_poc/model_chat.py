from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
import re

template = """
You are a helpful assistant. Please answer the user questions indicated by <user>...</user> as
good as possible. There may be relevant context indicated in <context>...</context> to help you
answer the user question. Respond directly after 'Response:' as part of the conversation.

<context>
{context}
</context>

<user>
{user_input}
</user>

Response:
"""

model = OllamaLLM(model="llama3.2")
prompt = ChatPromptTemplate.from_template(template)
chain = prompt | model

def chat():
    conversation_context = "conversation context:\n"
    print("Chat with Llama3.2. Type 'exit()' to end the conversation")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit()":
            break

        response = chain.invoke({"context": conversation_context, "user_input": user_input})
        print(f"Assistant: {response}")

        conversation_context += f"User:\n{user_input}\nAssistant:\n{response}\n"

    with open(f"history_{re.sub(r'[-:.]+', '_', datetime.now().isoformat())}.txt",
              "w", encoding="utf-8") as file:
        file.write(conversation_context)


if __name__ == "__main__":
    chat()
