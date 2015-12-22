import json
import yaml
#from rauth import OAuth1Service
from requests_oauthlib import OAuth1Session
import sys
from urllib import urlencode
from urlparse import parse_qsl, urlsplit, urlunsplit, parse_qsl



SERVICE = None

class SmugMugSession:

    OAUTH_ORIGIN = 'https://secure.smugmug.com'
    REQUEST_TOKEN_URL = OAUTH_ORIGIN + '/services/oauth/1.0a/getRequestToken'
    ACCESS_TOKEN_URL = OAUTH_ORIGIN + '/services/oauth/1.0a/getAccessToken'
    AUTHORIZE_URL = OAUTH_ORIGIN + '/services/oauth/1.0a/authorize'

    API_ORIGIN = 'https://api.smugmug.com'

    BASE_URL = API_ORIGIN + '/api/v2'

    client_key = None
    client_secret = None
    resource_owner_key = None
    resource_owner_secret = None

    def get_session(self):
        self.get_saved_oauth()
        if self.resource_owner_key == None or self.resource_owner_secret == None:
            self.get_access_token()

        oauth = OAuth1Session(self.client_key,
            client_secret=self.client_secret,
            resource_owner_key=self.resource_owner_key,
            resource_owner_secret=self.resource_owner_secret)

        return oauth


    def get_saved_oauth(self):
        try:
            with open('.sm_upload', 'r') as fh:
                config = yaml.load(fh)
        except IOError as e:
            print('====================================================')
            print('Failed to open .sm_upload! Did you create it?')
            print('====================================================')
            sys.exit(1)
        if type(config) is not dict \
                or 'key' not in config \
                or 'secret' not in config\
                or type(config['key']) is not str \
                or type(config['secret']) is not str:
            print('====================================================')
            print('Invalid config!')
            print('====================================================')

        self.client_key = config['key']
        self.client_secret = config['secret']

        if 'token' in config:
            self.resource_owner_key = config['token']
        if 'token_secret' in config:
            self.resource_owner_secret = config['token_secret']


    def get_access_token(self):

        oauth = OAuth1Session(self.client_key,client_secret=self.client_secret)
        fetch_response = oauth.fetch_request_token(REQUEST_TOKEN_URL)
        resource_owner_key = fetch_response.get('oauth_token')
        resource_owner_secret = fetch_response.get('oauth_token_secret')
        authorization_url = oauth.authorization_url(AUTHORIZE_URL)
        print 'Please go here and authorize,', authorization_url
        redirect_response = raw_input('Paste the full redirect URL here: ')
        oauth_response = oauth.parse_authorization_response(redirect_response)
        verifier = oauth_response.get('oauth_verifier')
        oauth = OAuth1Session(client_key,
          client_secret=client_secret,
          resource_owner_key=resource_owner_key,
          resource_owner_secret=resource_owner_secret,
          verifier=verifier)
        oauth_tokens = oauth.fetch_access_token(ACCESS_TOKEN_URL)
        self.access_token_key = oauth_tokens.get('oauth_token')
        self.access_token_secret = oauth_tokens.get('oauth_token_secret')

        save_tokens()



    def save_tokens():
        try:
            config = {}
            with open('.sm_upload', 'r') as fh:
                config = yaml.load(fh)
                config['token'] = self.access_token_key
                config['token_secret'] = self.access_token_secret
            with open('.sm_upload', 'w') as fh:
                fh.write(yaml.dump(config, default_flow_style=False))
        except IOError as e:
            print('====================================================')
            print('Failed to open .sm_upload! Did you create it?')
            print('====================================================')
            sys.exit(1)

    def add_auth_params(auth_url, access=None, permissions=None):
        if access is None and permissions is None:
            return auth_url
        parts = urlsplit(auth_url)
        query = parse_qsl(parts.query, True)
        if access is not None:
            query.append(('Access', access))
        if permissions is not None:
            query.append(('Permissions', permissions))
        return urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query, True),
            parts.fragment))
