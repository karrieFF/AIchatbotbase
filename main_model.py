# main.py
from chat_engine import GPTCoachEngine

def main():
    engine = GPTCoachEngine()
    print("Assistant:", engine.greeting)
    while True:
        user = input("You: ")
        if user.strip().lower() in {"exit", "quit"}:
            break
        ans, inputs, outputs = engine.chat(user)
        print("Assistant:", ans)
        print("Assistant:", inputs)
        print("Assistant", outputs)
        
if __name__ == "__main__":
    main()
