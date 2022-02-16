from setuptools import setup
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(name='locker-server',
        version='0.0.11',
        description='locker OpenID Connect file server',
        url='https://github.com/yaroslaff/locker-server',
        author='Yaroslav Polyakov',
        author_email='yaroslaff@gmail.com',
        license='GPL',
        packages=[
            'locker_server', 
            'locker_server.bp', 
            'locker_server.datafile'
        ],

        data_files = [
            ('locker/nginx',
                ['contrib/nginx/locker', 'contrib/nginx/locker-https']),
            ('locker/systemd', 
                ['contrib/systemd/locker-server.service']), 
            ('locker/uwsgi',
                ['contrib/uwsgi/locker.ini'])
        ], 
        include_package_data = True,


        scripts=['bin/locker-server.py'],

        long_description = read('README.md'),
        long_description_content_type='text/markdown',

        install_requires=[
            'flask', 
            'flask-login', 
            'flask-session',
            # 'flask-session @ git+https://github.com/yaroslaff/flask-session.git@samesite',
            'python-dotenv',
            'requests',
            'pyyaml',
            'redis',
            'oauthlib',
            'uwsgi',
            'flask-socketio'],

        zip_safe=True
      )

