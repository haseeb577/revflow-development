"""Background tasks"""
from app.celery_app import celery_app

@celery_app.task(name='validate_content_async')
def validate_content_async(content: str, title: str = None):
    from app.services.qa_validator import QAValidator
    from app.services.ai_detector import AIDetector
    
    validator = QAValidator()
    detector = AIDetector()
    qa_result = validator.validate(content, title)
    ai_result = detector.detect(content)
    
    return {
        'qa_score': qa_result.get('score', 0),
        'ai_probability': ai_result.get('probability', 0),
        'status': 'completed'
    }

@celery_app.task(name='batch_validate_async')
def batch_validate_async(batch_id: str, items: list):
    from app.services.qa_validator import QAValidator
    results = []
    validator = QAValidator()
    
    for idx, item in enumerate(items):
        try:
            qa_result = validator.validate(item['content'], item.get('title'))
            results.append({
                'content_id': item.get('content_id', f'item_{idx}'),
                'qa_score': qa_result.get('score', 0),
                'status': 'completed'
            })
        except Exception as e:
            results.append({'content_id': f'item_{idx}', 'error': str(e)})
    
    return {'batch_id': batch_id, 'results': results}
