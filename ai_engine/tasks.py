from celery import shared_task
import requests
from .sandbox import run_code_in_sandbox
from .models import ChatSession, Message

@shared_task(bind=True)
def generate_and_test_code(self, prompt: str, session_id: str = None):
    # 1. Fetch History if a session_id was provided
    history_payload = []
    
    if session_id:
        try:
            # Grab the last 4 messages from the database
            past_messages = Message.objects.filter(session_id=session_id).order_by('-created_at')[:4]
            # Reverse them so they are in chronological order
            for msg in reversed(past_messages):
                history_payload.append({
                    "role": msg.role,
                    "content": msg.content
                })
        except Exception as e:
            print(f"Database error: {e}")

    self.update_state(state='PROGRESS', meta={'status': 'Reading history & Asking the AI...'})
    
    # 2. Send prompt AND history to FastAPI
    try:
        payload = {
            "prompt": prompt,
            "history": history_payload
        }
        response = requests.post("http://127.0.0.1:8001/generate", json=payload)
        ai_generated_code = response.json().get('text', '# Error: No code generated')
    except Exception as e:
        ai_generated_code = f"print('Failed to connect to AI server: {str(e)}')"
    
    self.update_state(state='PROGRESS', meta={'status': 'Running in Docker Sandbox...'})
    
    # 3. Run it safely
    sandbox_result = run_code_in_sandbox(ai_generated_code)
    
    # 4. Save the AI's response to the Database
    if session_id:
        try:
            session = ChatSession.objects.get(id=session_id)
            Message.objects.create(
                session=session,
                role='ai',
                content=ai_generated_code,
                sandbox_output=sandbox_result.get('output', '') or sandbox_result.get('error', '')
            )
        except Exception as e:
            print(f"Failed to save AI message: {e}")

    # 5. Return everything to Next.js
    return {
        'code': ai_generated_code,
        'sandbox_logs': sandbox_result,
        'status': 'COMPLETED'
    }