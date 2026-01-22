import google.generativeai as genai
import os
from prompt_templates import get_system_prompt

class GeminiAgent:
    def __init__(self, player_id, role_name, partners=None, api_key=None):
        self.player_id = player_id
        self.role_name = role_name
        self.partners = partners
        
        # Configure API
        if api_key:
            genai.configure(api_key=api_key)
        else:
             # Try getting from env var if not passed
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
            else:
                # Fallback or error handling; for now assume it will be set globally or passed
                pass

        self.model = genai.GenerativeModel('gemini-2.0-flash') # Updated to available model
        
        system_instruction = get_system_prompt(role_name, player_id, partners)
        self.chat = self.model.start_chat(history=[
            {"role": "user", "parts": [system_instruction]}
        ])
        # Add a placeholder model response to acknowledge the system prompt
        self.chat.history.append({"role": "model", "parts": ["I understand my role and the rules. I am ready to play."]})

    def receive_message(self, message):
        """Append message to history without generating a response (simulating listening)."""
        # Gemini chat history is strictly User/Model. 
        # To simulate "listening" to others, we add it as a User message.
        # Format: "[Player X]: content"
        try:
            self.chat.history.append({"role": "user", "parts": [message]})
        except Exception as e:
            print(f"Error appending history for Agent {self.player_id}: {e}")

    def speak(self, context="It is your turn to speak. Be concise."):
        """Generate a response based on current history."""
        return self._safe_generate(context)

    def _safe_generate(self, context, retries=5):
        import time
        for i in range(retries):
            try:
                response = self.chat.send_message(context)
                return response.text.strip()
            except Exception as e:
                error_str = str(e)
                if "429" in error_str:
                    # Aggressive backoff for free tier: 10s, 20s, 30s, etc.
                    wait_time = 10 + (i * 10)
                    print(f"Agent {self.player_id} 触发频率限制 (429)。 {wait_time}秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"Agent {self.player_id} 发言生成错误: {e}")
                    return f"(错误: {e})"
        return "(错误: 重试失败)"

    def run_night_action(self, context):
        """Special method for night actions (killing, checking, saving/poisoning)."""
        return self._safe_generate(context)

    def run_vote_action(self, context="It is time to vote. Respond ONLY with the ID of the player you want to eliminate (e.g., '1' or '2'). If you abstain, say '-1'."):
        return self._safe_generate(context)
