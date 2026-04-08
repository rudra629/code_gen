from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch
import re
from typing import List

app = FastAPI()

print("Loading Base Model... (This might take a minute)")
model_id = "Qwen/Qwen2.5-Coder-1.5B"
tokenizer = AutoTokenizer.from_pretrained(model_id)

# Load the base model
base_model = AutoModelForCausalLM.from_pretrained(
    model_id, 
    torch_dtype=torch.float16, 
    device_map="auto"
)

print("Attaching your custom trained LoRA weights...")
model = PeftModel.from_pretrained(base_model, "./production-coder-lora")

# --- NEW: Define the Memory Structure ---
class MessageItem(BaseModel):
    role: str
    content: str

class PromptRequest(BaseModel):
    prompt: str
    history: List[MessageItem] = [] # Defaults to empty if it's a new chat

@app.post("/generate")
def generate_code(request: PromptRequest):
    
    # --- NEW: Reconstruct the Memory Block ---
    memory_block = ""
    # We only inject the last 4 messages so we don't overload the AI's RAM
    for msg in request.history[-4:]: 
        if msg.role == 'user':
            memory_block += f"User: {msg.content}\n"
        elif msg.role == 'ai':
            # We wrap the AI's past memory in backticks so it remembers it wrote code
            memory_block += f"Assistant:\n\x60\x60\x60python\n{msg.content}\n\x60\x60\x60\n"

    # Secretly force the AI to only write code
    strict_instruction = f"{request.prompt}\n\nIMPORTANT: Write ONLY valid, raw Python code. Do not write any English explanations. Do not use markdown blocks. your code is being reviewed by codex , opus 4.6 and gemini so make sure to follow best practices and write clean code."
    
    # Inject the memory right before the new prompt
    formatted_prompt = f"{memory_block}User: {strict_instruction}\nAssistant:\n"
    
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
    raw_output = raw_output.split("User:")[0].strip()
    
    if "\x60\x60\x60" in raw_output:
        parts = raw_output.split("\x60\x60\x60")
        if len(parts) >= 3:
            extracted_code = parts[1]
            if extracted_code.lower().startswith("python"):
                extracted_code = extracted_code[6:]
            final_code = extracted_code.strip()
        else:
            final_code = raw_output
    else:
        final_code = raw_output
        
    return {"text": final_code}