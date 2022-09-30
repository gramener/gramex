import os
import rasa


def train(handler):
    if handler.request.method == 'POST':
        chattrainer_kwargs = handler.kwargs.get('chattrainer_kwargs', {})
        config_dir = chattrainer_kwargs['config_dir']

        # Upload files
        for key in ['config.yml', 'nlu.yml', 'domain.yml', 'stories.yml', 'actions.py']:
            value = handler.get_arg(key, '')
            if len(value):
                with open(os.path.join(config_dir, key), 'w', newline='') as handle:
                    # TODO: Decode HTML
                    handle.write(value)

        # Retrain. TODO: Allow retaining to be optional
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
