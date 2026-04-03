from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

app = FastAPI()

print("Loading Base Model... (This might take a minute)")
model_id = "Qwen/Qwen2.5-Coder-1.5B"
tokenizer = AutoTokenizer.from_pretrained(model_id)

# Load the base model (we load it in 8-bit or standard depending on your PC's RAM)
base_model = AutoModelForCausalLM.from_pretrained(
    model_id, 
    torch_dtype=torch.float16, 
    device_map="auto" # Automatically uses GPU if you have one, else CPU
)

print("Attaching your custom trained LoRA weights...")
# This points to the folder you downloaded from Google Drive!
model = PeftModel.from_pretrained(base_model, "./production-coder-lora")

class PromptRequest(BaseModel):
    prompt: str

@app.post("/generate")
def generate_code(request: PromptRequest):
    
    # Secretly force the AI to only write code
    strict_instruction = f"{request.prompt}\n\nIMPORTANT: Write ONLY valid, raw Python code. Do not write any English explanations. Do not use markdown blocks. your code is being reviewed by codex , opus 4.6 and gemini so make sure to follow best practices and write clean code."
    
    # Format exactly how we trained it in Colab
    formatted_prompt = f"User: {strict_instruction}\nAssistant:\n"
    
    inputs = tokenizer(formatted_prompt, return_tensors="pt").to(model.device)
    
    # Generate the code
    outputs = model.generate(
        **inputs, 
        max_new_tokens=200, 
        temperature=0.1,    
        pad_token_id=tokenizer.eos_token_id
    )
    
    # Decode the text
    response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    raw_output = response_text.split("Assistant:\n")[-1].strip()
    
    # --- THE BULLETPROOF SANITIZER ---
    
    # 1. Stop the AI from hallucinating a fake user conversation
    raw_output = raw_output.split("User:")[0].strip()
    
    # 2. Extract code block using standard Python splitting (no regex bugs!)
    if "```" in raw_output:
        parts = raw_output.split("```")
        # The code is usually in the second block between the backticks
        if len(parts) >= 3:
            extracted_code = parts[1]
            # Strip the word "python" if it added it to the top of the block
            if extracted_code.lower().startswith("python"):
                extracted_code = extracted_code[6:]
            final_code = extracted_code.strip()
        else:
            final_code = raw_output
    else:
        final_code = raw_output
        
    return {"text": final_code}