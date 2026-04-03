from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from celery.result import AsyncResult
import json
from .tasks import generate_and_test_code

@csrf_exempt 
def trigger_generation(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        prompt = data.get('prompt')
        task = generate_and_test_code.delay(prompt)
        return JsonResponse({'task_id': task.id}, status=202)

def check_status(request, task_id):
    task_result = AsyncResult(task_id)
    response_data = {'task_id': task_id, 'status': task_result.status}

    if task_result.status == 'SUCCESS':
        response_data['result'] = task_result.result
    elif task_result.status == 'PROGRESS':
        response_data['meta'] = task_result.info 

    return JsonResponse(response_data)