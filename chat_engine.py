import torch
from model_loader import load_model
from text_cleaner import clean_response
from prompt_template import build_prompt  # your MI-style starter

class GPTCoachEngine:
    def __init__(self):
        # load once
        self.tokenizer, self.model = load_model()
        self.model.eval()

        # make greeting once
        self.greeting = self._make_greeting()

        # base MI prompt once
        self.messages = build_prompt("Hi, I'd like to get some help with my physical activity.")
        self.messages.append({"role": "assistant", "content": self.greeting})

    def _make_greeting(self):
        greeting_prompt = (
            "You are GPTCoach, a friendly health coach. "
            "Introduce yourself briefly (<=50 words) and invite the user to share their goals."
        )
        greet_messages = [{"role": "system", "content": greeting_prompt}]

        chat_text = self.tokenizer.apply_chat_template(
            greet_messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(chat_text, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=80,
                temperature=0.6,
                top_p=0.9,
                do_sample=True,
            )

        # decode only generated part
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return clean_response(text)

    def chat(self, user_text: str) -> str:
        """One turn of chat: add user → generate → clean → add assistant → return text."""
        # add user message
        self.messages.append({"role": "user", "content": user_text})

        chat_text = self.tokenizer.apply_chat_template(
            self.messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.tokenizer(chat_text, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=80,
                temperature=0.6,
                top_p=0.9,
                do_sample=True,
            )

        # decode only new tokens
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        response = clean_response(response)

        # add assistant turn
        self.messages.append({"role": "assistant", "content": response})

        return response
    

