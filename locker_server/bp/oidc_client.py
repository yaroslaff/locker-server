
import requests
import json
import os
import logging
import random
import string
from urllib.parse import urljoin, urlparse, urlunparse

from oauthlib.oauth2 import WebApplicationClient
import redis

from flask import Blueprint, request, redirect, session, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)


from ..app import App
from ..user import User, UserNotFound
from ..datafile import BindingsFile
from ..config import config

oidc_bp = Blueprint('oidc', __name__)

# r = redis.Redis(host='localhost', port=6379, db=0)
r = redis.Redis(decode_responses=True)

log = logging.getLogger()


@oidc_bp.route('/hello')
def hello():
    x = session.get('x', 0)
    session['x'] = x+1
    return f'Hello ({x})'

def get_provider_cfg(url):
    return requests.get(url).json()

@oidc_bp.route("/login/<provider>", methods=['POST'])
def login(provider):
    app = App()
    app.check_origin()    


    credentials = app.get_credentials(provider)
    client = WebApplicationClient(credentials['CLIENT_ID'])
    provider_cfg = get_provider_cfg(credentials['DISCOVERY_URL'])
    
    authorization_endpoint = provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google

    if 'AUTH_HOST' in config:
        redirect_uri = f'https://{config["AUTH_HOST"]}/oidc/callback'
    else:
        redirect_uri=urljoin(request.url_root, "/oidc/callback")

    
    alphabet = string.ascii_lowercase + string.digits
    state = ''.join(random.choice(alphabet) for i in range(10))

    key = f'locker-oidc-login:{state}'
    data = {
        'state': state,
        'provider': provider,
        'locker_app_url': request.url_root,
    }
    r.hset(key, mapping=data)
    r.expire(key, int(config['AUTH_TIMEOUT']))

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=redirect_uri,
        scope=["openid", "email", "profile"],
        state=state
    )
    session['oidc_provider'] = provider
    session['oidc_return'] = request.args.get('return')
    return redirect(request_uri)

@oidc_bp.route("/bind/<provider>")
def bind(provider):
    session['want_bind'] = provider
    return login(provider)

@oidc_bp.route("/callback")
def callback():

    def get_redirect_url():
        target_host = urlparse(data['locker_app_url']).netloc
        parts = urlparse(request.url)
        target = urlunparse(parts._replace(netloc=target_host))
        return target

    # Get authorization code Google sent back to you
    code = request.args.get("code")
    state = request.args.get("state")

    key = f'locker-oidc-login:{state}'
    data = r.hgetall(key)

    if not data:
        return "Login session expired. Please return to application and login again."

    provider = data['provider']

    if 'AUTH_HOST' in config and request.host == config['AUTH_HOST']:
        r.hset(key, 'request.url', request.url)
        r.hset(key, 'request.base_url', request.base_url)

        return redirect(get_redirect_url())

    r.delete(key)
    app = App()

    app.log("OIDC callback")
    app.log(f"{dir(session)}")
    app.log(f"{session['uid']}")

    if 'Origin' in request.headers:
        app.cross_response('Must have empty Origin headers in callback!', 400)

    app_opts = app.get_config('etc/options.json')

    credentials = app.get_credentials(provider)
    client = WebApplicationClient(credentials['CLIENT_ID'])
    provider_cfg = get_provider_cfg(credentials['DISCOVERY_URL'])

    token_endpoint = provider_cfg["token_endpoint"]

    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=data['request.url'],
        redirect_url=data['request.base_url'],
        code=code
    )

    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(
            credentials['CLIENT_ID'], 
            credentials['CLIENT_SECRET'])
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Now that you have tokens (yay) let's find and hit the URL
    # from Google that gives you the user's profile information,
    # including their Google profile image and email
    userinfo_endpoint = provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!

    userinfo = userinfo_response.json()
    sub = userinfo['sub']

    if not userinfo["email_verified"]:
        msg = f"User email not available or not verified by {provider}."
        app.log(msg)
        return msg, 400

    # Create a user in your db with the information provid`ed
    # by Google

    with BindingsFile(app.localpath('etc/users.json')) as uf:
        username = uf.get_binding(provider, sub)
        app.log(f"username: {username}")

    if username:
        if not current_user.is_authenticated:
            """ usual login user """
            user = User.get(app, username)
            login_user(user)
            session['userinfo'] = userinfo
            session.permanent = True
            app.log(f"login user: {username}")
    else:
        """ no such binding """
        app.log("no binding")
        # Maybe no need to create?
        if not app.accept_new_users():
            app.log("not accepting new users")
            try:
                redirect_url = app_opts['noregister_url']
                return redirect(redirect_url)
            except KeyError:
                return 'New user registration is forbidden'

        if current_user.is_authenticated:
            app.log("already authenticated, want bind?")
            # make new binding
            if session.get('want_bind') == provider:
                with BindingsFile(app.localpath('etc/users.json'), 'rw') as uf:
                    app.log(f"bind to {provider}")
                    uf.bind(provider, sub, current_user.id)
                del session['want_bind']

        else:
            app.log("create user")
            # create user
            with BindingsFile(app.localpath('etc/users.json'), 'rw') as uf:
                username = uf.create(provider, sub)
                app.log(f"created user {username}")

            user = User(
                    id_ = username, 
                    app = app, 
                    userinfo = userinfo
            )
            user.create()
            login_user(user)
            session['userinfo'] = userinfo
            session.permanent = True
            app.log(f"Logged in new user {username}")

    return redirect(session['oidc_return'] or app_opts['return_url'])
