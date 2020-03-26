import os
from .. import checker

import flask

def main():
    filename = os.environ.get('AGNI_SETTINGS', None)

    if filename is None:
        print('This program require AGNI_SETTINGS environment')
        return
    print(filename)

    file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '../../')

    settings = flask.config.Config(file_path)
    settings.from_object('agni.default_settings')
    settings.from_envvar('AGNI_SETTINGS', silent=True)

    # with open(filename, mode='rb') as config_file:
    #     exec(compile(config_file.read(), filename, 'exec'), settings)

    # settings.pop('__builtins__')

    checker_server = checker.Server(settings)

    checker_server.run()
   


