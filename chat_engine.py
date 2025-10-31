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

        # # base MI prompt once
        self.messages = build_prompt("") #"Hi, I'd like to get some help with my physical activity."
        self.messages.append({"role": "assistant", "content": self.greeting})

    def _make_greeting(self):
        greeting_prompt = (
            "You are a friendly health coach using motivational interviewing coach. "
            "Introduce yourself briefly (<=30 words) and invite the user to talk about themselves."
        )
        greet_messages = [{"role": "system", "content": greeting_prompt}]

        chat_text = self.tokenizer.apply_chat_template(
            greet_messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self.tokenizer(chat_text, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=60,
                temperature=0.3,
                top_p=0.7, #lower top_p, more creative:0.6-0.8
                do_sample=True,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        # decode only generated part
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return clean_response(text)

# # ----- session helpers -----
#     def _init_session(self, session_id: str, keep_greeting: bool = True) -> None:
#         messages = build_prompt("")
#         if len(messages) >= 2 and messages[1].get("role") == "user" and messages[1].get("content", "") == "":
#             messages = [messages[0]]
#         if keep_greeting:
#             messages.append({"role": "assistant", "content": self.greeting})
#         self.sessions[session_id] = messages

#     def _get_session_messages(self, session_id: str) -> List[Message]:
#         if session_id not in self.sessions:
#             self._init_session(session_id)
#         return self.sessions[session_id]

#     def _truncate_history(self, msgs: List[Message]) -> List[Message]:
#         if self.max_turns is None:
#             return msgs
#         system = msgs[0:1]
#         rest = msgs[1:]
#         need = 2 * self.max_turns
#         if len(rest) > need:
#             rest = rest[-need:]
#         return system + rest

#     # ----- user memory -----
#     def _memory_system_message(self, user_id: Optional[str]) -> Optional[Message]:
#         if not user_id:
#             return None
#         summary = self.user_memory.get(user_id, "").strip()
#         if not summary:
#             return None
#         return {
#             "role": "system",
#             "content": "Known user memory (verify before using; never assume):\n" + summary,
#         }

#     def _update_user_memory(self, user_id: Optional[str], session_msgs: List[Message]) -> None:
#         if not user_id:
#             return
#         recent = session_msgs[-6:] if len(session_msgs) > 6 else session_msgs
#         text_block = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent if m.get("content")])

#         prompt = [
#             {"role": "system", "content": (
#                 "You maintain a brief user memory for MI coaching. Extract only stable facts explicitly stated "
#                 "by the user: demographics, preferences, constraints, goals, current plan. 1–4 short lines. "
#                 "No advice, no numbered lists."
#             )},
#             {"role": "user", "content": f"Conversation:\n{text_block}\n\nCurrent memory:\n{self.user_memory.get(user_id, '')}\n\nUpdate the memory succinctly:"}
#         ]
#         chat_text = self.tokenizer.apply_chat_template(prompt, tokenize=False, add_generation_prompt=True)
#         inputs = self.tokenizer(chat_text, return_tensors="pt").to(self.model.device)
#         with torch.no_grad():
#             outputs = self.model.generate(
#                 **inputs,
#                 max_new_tokens=120,
#                 temperature=0.2,
#                 top_p=0.6,
#                 do_sample=False,
#                 eos_token_id=self.tokenizer.eos_token_id,
#             )
#         new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
#         out = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
#         self.user_memory[user_id] = clean_response(out)

    def chat(self, user_text: str) -> str:
        """One turn of chat: add user → generate → clean → add assistant → return text."""
        
        # this is for transfer the user text to the computer lanaugage
        # add user message
        self.messages.append({"role": "user", "content": user_text})

        chat_text = self.tokenizer.apply_chat_template(
            self.messages,
            tokenize=False,
            add_generation_prompt=True,
        ) #tokenizer is a tool to convert text into tokens

        inputs = self.tokenizer(chat_text, return_tensors="pt").to(self.model.device)


        #generate outputs based on inputs computer lanaguage
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=80, #lower, lower creativity: 60-80
                temperature=0.4, #lower temparature, lower creatively: 0.2-0.4
                top_p=0.7, #lower top_p, more creative:0.6-0.8
                do_sample=True,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        # decode only new tokens
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        response = clean_response(response)

        # add assistant turn, add human 
        self.messages.append({"role": "assistant", "content": response})

        return response
    

