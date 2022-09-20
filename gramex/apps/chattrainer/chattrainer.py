import os
import rasa


def train(handler):
    if handler.request.method == 'POST':
        chattrainer_kwargs = handler.kwargs.get('chattrainer_kwargs', {})
        config_dir = chattrainer_kwargs['config_dir']
        rasa.train(
            domain=os.path.join(config_dir, 'domain.yml'),
            config=os.path.join(config_dir, 'config.yml'),
            training_files=[
                os.path.join(config_dir, 'nlu.yml'),
                os.path.join(config_dir, 'stories.yml'),
            ],
            output=config_dir)
    else:
        handler.write('Use POST method to train')
