"""Data utilities."""
import os
import json
import gramex.cache

directory = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(directory, 'quiz.yaml')


def quiz_config():
    """Return questions."""
    return json.dumps(gramex.cache.open(
        config_path, 'config'), ensure_ascii=True, indent=2)


def quiz_results(handler):
    """Evaluate answers."""
    questions = gramex.cache.open(config_path, 'config')['questions']
    real_answers = {qset: questions[qset]['answer'] for ind, qset in enumerate(questions)}
    user_answers = {
        x: handler.get_argument('option-{}'.format(x), None)
        for x in range(1, 10)
    }
    score = 0
    for key in real_answers:
        if user_answers[key] and user_answers[key] == real_answers[key]:
            score += 1
    return {'score': score}
