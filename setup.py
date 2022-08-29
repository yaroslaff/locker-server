from setuptools import setup
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(name='locker-server',
        version='0.0.17',
        description='locker OpenID Connect file server',
        url='https://github.com/yaroslaff/locker-server',
        author='Yaroslav Polyakov',
        author_email='yaroslaff@gmail.com',
        license='GPL',
        packages=[
            'locker_server', 
            'locker_server.bp', 
            'locker_server.datafile',
            'locker_server.misc'
        ],

        data_files = [
            ('locker/nginx',
                ['contrib/nginx/sites-available/locker-https']),
            ('locker/systemd', 
                ['contrib/systemd/locker-server.service']), 
            ('locker/uwsgi',
                ['contrib/uwsgi/locker.ini'])
        ], 
        include_package_data = True,


        scripts=[
            'bin/locker-server.py',
            'bin/lsadm.py',
            'bin/mkvhost.py'],

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

