
from better_profanity import profanity
from datetime import datetime, timezone
from django.conf import settings
from api.common.utils import prompts
from api.computer.models import Computer
import re
import groq

class ChatbotService:


    tagalog_profanity = settings.TAGALOG_PROFANITY_WORDS

    custom_words = list({
        word.strip().lower()
        for word in tagalog_profanity.split(",")
        if word.strip()
    })

    profanity.load_censor_words()
    profanity.add_censor_words(custom_words)

    system_prompt = prompts.load_prompt('chat-rules.md')
        
    
    @staticmethod
    def process_conversation(session, user_message):

        if ChatbotService.is_session_expired(session):
            session.flush()

        error = ChatbotService.clean_input(user_message)
        if error:
            return {"reply": error, "error": True}
        
        computer_context = None
        
        match = re.search(r"\bPC\d{9}\b", user_message)

        if match:
            computer_code = match.group()

            computer = Computer.objects.filter(
                computer_code=computer_code
            ).select_related('room').first()

            if computer:
                computer_context = f"""
                    Computer information from the database:

                    Computer Code: {computer.computer_code}
                    CPU: {computer.cpu}
                    GPU: {computer.gpu}
                    Motherboard: {computer.motherboard}
                    RAM: {computer.ram_size_installed} GB
                    Disk: {computer.disk_size_installed} GB
                    Operating System: {computer.operating_system}
                    Room: {computer.room.room_name}
                    Building: {computer.room.building_name}
                    Status: {computer.computer_status}

                    Peripheral status
                    Monitor: {computer.monitor_status}
                    Mouse: {computer.mouse_status}
                    Keyboard: {computer.keyboard_status}
                    UPS: {computer.ups_status}
                    Use this information when answering the user's question.
                    """
        
        history = session.get('conversation', [])
        messages = ChatbotService.build_messages(history, user_message, computer_context)
        reply = ChatbotService.call_ai(messages)

        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        session['conversation'] = history
        session['last_active'] = datetime.now(timezone.utc).timestamp()
        session.modified = True
        
        return {"reply": reply, "error": False}
        
    @staticmethod
    def clean_input(text):
        if profanity.contains_profanity(text):
            return "Please keep the conversation professional."
        return None
    
    @staticmethod
    def is_session_expired(session):
        last_active = session.get('last_active')
        
        if not last_active:
            return False
        now = datetime.now(timezone.utc).timestamp()
        return(now - last_active) > settings.SESSION_AGE
    

    @staticmethod
    def build_messages(history, user_message, context=None):
        trimmed = history[-(settings.MAX_HISTORY * 2):]

        messages = [
            {"role": "system", "content": ChatbotService.system_prompt},
        ]

        if context:
            messages.append({
                "role": "system",
                "content": context,
            })

        messages.extend(trimmed)

        messages.append({
            "role": "user",
            "content": user_message,
        })

        return messages
    
    @staticmethod
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

        


    