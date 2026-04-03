from celery import shared_task
import requests
from .sandbox import run_code_in_sandbox

@shared_task(bind=True)
def generate_and_test_code(self, prompt: str):
    # 1. Update Frontend Status
    self.update_state(state='PROGRESS', meta={'status': 'Asking the AI Brain...'})
    
    # 2. Ping your new local FastAPI Microservice
    try:
        # We assume the AI server is running on port 8001
        response = requests.post("http://127.0.0.1:8001/generate", json={"prompt": prompt})
        ai_generated_code = response.json().get('text', '# Error: No code generated')
    except Exception as e:
        ai_generated_code = f"print('Failed to connect to AI server: {str(e)}')"
    
    # 3. Update Frontend Status
    self.update_state(state='PROGRESS', meta={'status': 'Running in Docker Sandbox...'})
    
    # 4. Run it safely
    sandbox_result = run_code_in_sandbox(ai_generated_code)
    
    # 5. Return everything
    return {
        'code': ai_generated_code,
        'sandbox_logs': sandbox_result,
        'status': 'COMPLETED'
    }