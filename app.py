import json
import os
import urllib.error
import urllib.parse
import urllib.request

import oauth2 as oauth
import requests
from flask import Flask, render_template, request, url_for

# from flask_session.__init__ import Session

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.debug = True

# SESSION_TYPE = 'filesystem'
# app.config.from_object(__name__)
# Session(app)

request_token_url = 'https://api.twitter.com/oauth/request_token'
access_token_url = 'https://api.twitter.com/oauth/access_token'
authorize_url = 'https://api.twitter.com/oauth/authorize'
show_user_url = 'https://api.twitter.com/1.1/users/show.json'

# Support keys from environment vars (Heroku).
app.config['APP_CONSUMER_KEY'] = os.getenv('APP_CONSUMER_KEY')
app.config['APP_CONSUMER_SECRET'] = os.getenv('APP_CONSUMER_SECRET')
app.config['APP_BEARER_TOKEN'] = os.getenv('APP_BEARER_TOKEN')
# app.config['APP_BEARER_TOKEN'] = 'os.getenv('APP_BEARER_TOKEN')'
# alternatively, add your key and secret to config.cfg
# config.cfg should look like:
# APP_CONSUMER_KEY = 'API_Key_from_Twitter'
# APP_CONSUMER_SECRET = 'API_Secret_from_Twitter'
app.config.from_pyfile('config.cfg', silent=True)

oauth_store = {}
user_followers = {}
user_info = {}


@app.route('/')
def hello():
    return render_template('index.html')


def connect_to_endpoint(url, headers, params):
    response = requests.request("GET", url, headers=headers, params=params)
    print(response.status_code)
    if response.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text
            )
        )
    return response.json()


@app.route('/custompage')
def custompage():
    bearer_token = app.config['APP_BEARER_TOKEN']
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    get_user_id_url = f'https://api.twitter.com/2/users/by/username/yayboechat'
    json_response = connect_to_endpoint(get_user_id_url, headers, params={})

    user_id = json_response['data']['id']
    url = f'https://api.twitter.com/2/users/{user_id}/following?max_results=10'
    params = {"user.fields": "created_at"}
    json_response = connect_to_endpoint(url, headers, params)
    print(json.dumps(json_response, indent=4, sort_keys=True))

    return render_template('custompage.html')


@app.route('/start')
def start():
    # note that the external callback URL must be added to the whitelist on
    # the developer.twitter.com portal, inside the app settings
    app_callback_url = url_for('callback', _external=True)

    # Generate the OAuth request tokens, then display them
    consumer = oauth.Consumer(
        app.config['APP_CONSUMER_KEY'], app.config['APP_CONSUMER_SECRET'])
    client = oauth.Client(consumer)
    resp, content = client.request(request_token_url, "POST", body=urllib.parse.urlencode({
        "oauth_callback": app_callback_url}))

    if resp['status'] != '200':
        error_message = 'Invalid response, status {status}, {message}'.format(
            status=resp['status'], message=content.decode('utf-8'))
        return render_template('error.html', error_message=error_message)

    request_token = dict(urllib.parse.parse_qsl(content))
    oauth_token = request_token[b'oauth_token'].decode('utf-8')
    oauth_token_secret = request_token[b'oauth_token_secret'].decode('utf-8')

    oauth_store[oauth_token] = oauth_token_secret

    return render_template('start.html', authorize_url=authorize_url, oauth_token=oauth_token,
                           request_token_url=request_token_url, message='hello guys')


@app.route('/callback')
def callback():
    # Accept the callback params, get the token and call the API to
    # display the logged-in user's name and handle
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    oauth_denied = request.args.get('denied')

    # if the OAuth request was denied, delete our local token
    # and show an error message
    if oauth_denied:
        if oauth_denied in oauth_store:
            del oauth_store[oauth_denied]
        return render_template('error.html', error_message="the OAuth request was denied by this user")

    if not oauth_token or not oauth_verifier:
        return render_template('error.html', error_message="callback param(s) missing")

    # unless oauth_token is still stored locally, return error
    if oauth_token not in oauth_store:
        return render_template('error.html', error_message="oauth_token not found locally")

    oauth_token_secret = oauth_store[oauth_token]

    # if we got this far, we have both callback params and we have
    # found this token locally

    consumer = oauth.Consumer(
        app.config['APP_CONSUMER_KEY'], app.config['APP_CONSUMER_SECRET'])
    token = oauth.Token(oauth_token, oauth_token_secret)
    token.set_verifier(oauth_verifier)
    client = oauth.Client(consumer, token)

    resp, content = client.request(access_token_url, "POST")
    access_token = dict(urllib.parse.parse_qsl(content))

    screen_name = access_token[b'screen_name'].decode('utf-8')
    user_id = access_token[b'user_id'].decode('utf-8')

    # These are the tokens you would store long term, someplace safe
    real_oauth_token = access_token[b'oauth_token'].decode('utf-8')
    real_oauth_token_secret = access_token[b'oauth_token_secret'].decode(
        'utf-8')

    # Call api.twitter.com/1.1/users/show.json?user_id={user_id}
    real_token = oauth.Token(real_oauth_token, real_oauth_token_secret)
    real_client = oauth.Client(consumer, real_token)
    real_resp, real_content = real_client.request(
        show_user_url + '?user_id=' + user_id, "GET")

    if real_resp['status'] != '200':
        error_message = "Invalid response from Twitter API GET users/show: {status}".format(
            status=real_resp['status'])
        return render_template('error.html', error_message=error_message)

    response = json.loads(real_content.decode('utf-8'))

    friends_count = response['friends_count']
    statuses_count = response['statuses_count']
    followers_count = response['followers_count']
    name = response['name']

    # don't keep this token and secret in memory any longer
    # session['own_id'] = user_id
    user_info['own_id'] = user_id
    del oauth_store[oauth_token]

    return render_template('callback-success.html', screen_name=screen_name, user_id=user_id, name=name,
                           friends_count=friends_count, statuses_count=statuses_count,
                           followers_count=followers_count, access_token_url=access_token_url)


looked_id = []


@app.route('/friendaction', methods=['POST', 'GET'])
def get_post_javascript_data():
    bearer_token = app.config['APP_BEARER_TOKEN']
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    if request.method == 'POST':
        jsdata_username = request.form['javascript_data']
        get_user_id_url = f'https://api.twitter.com/2/users/by/username/{jsdata_username}'
        user_lookup_info = connect_to_endpoint(get_user_id_url, headers, params={})
        looked_id.append(user_lookup_info['data']['id'])
    else:
        user_id = looked_id[-1]
        url = f'https://api.twitter.com/2/users/{user_id}/following?max_results=5'
        params = {"user.fields": "created_at"}
        json_get_response = connect_to_endpoint(url, headers, params)
        json_get_response['main_node'] = {
            "user_id": user_id,
        }
        #
        # print('rede do amigo')
        #
        # print(json_get_response['data'][0])
        # print(json.dumps(json_get_response, indent=4, sort_keys=True))

        return json_get_response

    return user_lookup_info


own_id = ""


@app.route('/selfnetaction', methods=['GET'])
def get_selfnet():
    bearer_token = app.config['APP_BEARER_TOKEN']
    headers = {"Authorization": "Bearer {}".format(bearer_token)}

    # user_id = session.get('own_id')
    user_id = user_info['own_id']
    url = f'https://api.twitter.com/2/users/{user_id}/following?max_results=5'
    params = {"user.fields": "created_at"}
    json_get_response = connect_to_endpoint(url, headers, params)
    json_get_response['main_node'] = {
        "user_id": user_id,
    }

    return json_get_response


@app.route('/nextnet', methods=['GET'])
def get_nextnet():
    bearer_token = app.config['APP_BEARER_TOKEN']
    headers = {"Authorization": "Bearer {}".format(bearer_token)}

    user_id = request.args.get('user_id')
    url = f'https://api.twitter.com/2/users/{user_id}/following?max_results=5'
    print(url)
    params = {"user.fields": "created_at"}
    json_get_response = connect_to_endpoint(url, headers, params)

    return json_get_response


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_message='uncaught exception'), 500


if __name__ == '__main__':
    # sess = Session()
    # sess.init_app(app)

    app.run(use_reloader=True)
