import docker
import tempfile
import os

def run_code_in_sandbox(code_str: str) -> dict:
    client = docker.from_env()

    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = os.path.join(temp_dir, 'script.py')
        
        with open(script_path, 'w') as f:
            f.write(code_str)

        try:
            container_output = client.containers.run(
                image="python:3.10-alpine",
                command="python /app/script.py",
                volumes={temp_dir: {'bind': '/app', 'mode': 'ro'}}, 
                working_dir="/app",
                remove=True,            
                mem_limit="128m",       
                network_disabled=True,  
                stderr=True,
                stdout=True
            )
            return {"success": True, "output": container_output.decode('utf-8').strip()}

        except docker.errors.ContainerError as e:
            return {"success": False, "error": e.stderr.decode('utf-8').strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}