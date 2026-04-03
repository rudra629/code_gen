from celery import shared_task
import time
from .sandbox import run_code_in_sandbox

@shared_task(bind=True)
def generate_and_test_code(self, prompt: str):
    # 1. Update Frontend Status
    self.update_state(state='PROGRESS', meta={'status': 'Generating code with AI...'})
    
    # 2. Simulate the AI generating code (We will connect your Colab model here later)
    time.sleep(2) 
    ai_generated_code = f"""
def handle_prompt():
    print("AI processed: {prompt}")
    return "Code Execution Successful!"

print(handle_prompt())
"""
    
    # 3. Update Frontend Status
    self.update_state(state='PROGRESS', meta={'status': 'Running in Docker Sandbox...'})
    
    # 4. Run it safely
    sandbox_result = run_code_in_sandbox(ai_generated_code)
    
    # 5. Return everything to Next.js
    return {
        'code': ai_generated_code,
        'sandbox_logs': sandbox_result,
        'status': 'COMPLETED'
    }