
from better_profanity import profanity
from datetime import datetime, timezone
from django.conf import settings
from api.common.utils import prompts
import groq

class ChatbotService:

    profanity.load_censor_words()

    system_prompt = prompts.load_prompt('chat-rules.md')
        
    
    @staticmethod
    def process_conversation(session, user_message):

        if ChatbotService.is_session_expired(session):
            session.flush()

        error = ChatbotService.clean_input(user_message)
        if error:
            return {"reply": error, "error": True}
        
        history = session.get('conversation', [])

        messages = ChatbotService.build_messages(history, user_message)
        reply = ChatbotService.call_ai(messages)

        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        session['conversation'] = history
        session['last_active'] = datetime.now(timezone.utc).timestamp()
        session.modified = True
        
        return {"reply": reply, "error": False}
        
    
    def clean_input(text):
        if profanity.contains_profanity(text):
            return None, "Please keep the conversation professional."
        return None
    
    def is_session_expired(session):
        last_active = session.get('last_active')
        
        if not last_active:
            return False
        now = datetime.now(timezone.utc).timestamp()
        return(now - last_active) > settings.SESSION_AGE
    

    def build_messages(history, user_message):
        trimmed = history[-(settings.MAX_HISTORY * 2):]
        return [
            {"role": "system", "content": ChatbotService.system_prompt},
            *trimmed,
            {"role": "user", "content": user_message}
        ]
    
    def call_ai(messages):

        groq_models = [
            "llama-3.3-70b-versatile",       
            "openai/gpt-oss-120b",           
            "qwen/qwen3-32b",                
            "meta-llama/llama-4-scout-17b-16e-instruct",  
            "llama-3.1-8b-instant", 
        ]

        client = groq.Groq(api_key=settings.GROQ_API_KEY)

        for model in groq_models:
            try:
                completion = client.chat.completions.create(
                    model = model,
                    messages= messages
                )

                return completion.choices[0].message.content
            except groq.RateLimitError:
                print(f"Rate Limit Exceeded on model: {model}")
                continue
            except groq.BadRequestError as e:
                print(f"Bad Request Error: {str(e)}")
                return None, f"Bad Request Error: {str(e)}"
        
        return None, "All models exhausted"

        


    