from oauthlib.oauth2 import WebApplicationClient
import requests
import json
from urllib.parse import urljoin

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
from ..datafile import UserFile

oidc_bp = Blueprint('oidc', __name__)

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

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=urljoin(request.url_root, "/oidc/callback"),
        scope=["openid", "email", "profile"],
    )
    session['oidc_provider'] = provider
    session['oidc_return'] = request.args.get('return')
    
    print("LOGIN")
    print("REDIRECT TO", request_uri)
    print("url_root:", request.url_root)
    
    return redirect(request_uri)

@oidc_bp.route("/bind/<provider>")
def bind(provider):
    session['want_bind'] = provider
    return login(provider)

@oidc_bp.route("/callback")
def callback():

    # Get authorization code Google sent back to you
    code = request.args.get("code")

    provider = session['oidc_provider']

    print("CALLBACK")
    print("code:", code)
    print("PROVIDER:", session['oidc_provider'])

    app = App()
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
        authorization_response=request.url,
        redirect_url=request.base_url,
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
        return f"User email not available or not verified by {provider}.", 400

    # Create a user in your db with the information provided
    # by Google

    with UserFile(app.localpath('etc/users.json')) as uf:
        username = uf.get_binding(provider, sub)

    if username:
        if not current_user.is_authenticated:
            """ usual login user """
            user = User.get(app, username)
            login_user(user)
            session['userinfo'] = userinfo
            session.permanent = True
    else:
        """ no such binding """
        # Maybe no need to create?
        if not app.accept_new_users():
            try:
                redirect_url = app_opts['noregister_url']
                return redirect(redirect_url)
            except KeyError:
                return 'New user registration is forbidden'

        if current_user.is_authenticated:
            # make new binding
            if session.get('want_bind') == provider:
                with UserFile(app.localpath('etc/users.json'), 'rw') as uf:
                    uf.bind(provider, sub, current_user.id)
                del session['want_bind']

        else:
            # create user
            with UserFile(app.localpath('etc/users.json'), 'rw') as uf:
                username = uf.create(provider, sub)

            user = User(
                    id_ = username, 
                    app = app, 
                    userinfo = userinfo
            )
            user.create()
            login_user(user)
            session['userinfo'] = userinfo
            session.permanent = True

    # print("return to:", app_opts['return_url'])
    return redirect(session['oidc_return'] or app_opts['return_url'])
