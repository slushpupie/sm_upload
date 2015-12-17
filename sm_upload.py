#!/usr/bin/env python
from rauth import OAuth1Session
import sys

from common import API_ORIGIN, get_service, add_auth_params, load_tokens, save_tokens
from urllib import urlencode

import pprint
pp = pprint.PrettyPrinter(indent=4)

session
def main():
    """This example interacts with its user through the console, but it is
    similar in principle to the way any non-web-based application can obtain an
    OAuth authorization from a user."""

    service = get_service()

    t = load_tokens()
    at = t['token']
    ats = t['token_secret']

    if at == None or ats == None:

        # First, we need a request token and secret, which SmugMug will give us.
        # We are specifying "oob" (out-of-band) as the callback because we don't
        # have a website for SmugMug to call back to.
        rt, rts = service.get_request_token(params={'oauth_callback': 'oob'})

        # Second, we need to give the user the web URL where they can authorize our
        # application.
        auth_url = add_auth_params(
                service.get_authorize_url(rt), access='Full', permissions='Modify')
        print('Go to %s in a web browser.' % auth_url)

        # Once the user has authorized our application, they will be given a
        # six-digit verifier code. Our third step is to ask the user to enter that
        # code:
        sys.stdout.write('Enter the six-digit code: ')
        sys.stdout.flush()
        verifier = sys.stdin.readline().strip()

        # Finally, we can use the verifier code, along with the request token and
        # secret, to sign a request for an access token.
        at, ats = service.get_access_token(rt, rts, params={'oauth_verifier': verifier})

        # The access token we have received is valid forever, unless the user
        # revokes it.  Let's make one example API request to show that the access
        # token works.
        print('Access token: %s' % at)
        print('Access token secret: %s' % ats)
        save_tokens(at,ats)

    session = OAuth1Session(
            service.consumer_key,
            service.consumer_secret,
            access_token=at,
            access_token_secret=ats)

    node = getLocalNode('.')
    if not node:
        userObj = session.get(API_ORIGIN + '/api/v2/user/slushpupie',
                headers={'Accept': 'application/json'}).json()
        nodeUri = userObj['Response']['User']['Uris']['Node']['Uri'])
        node = getRemoteNode(nodeUri)
        saveLocalNode('.',node)


def image_exist(node,image_name):
    

def getNode(folder):
    node = getLocalNode(folder)
    if node:
        return node

    node = getRemoteNode(folder)
    if node:
        saveLocalNode(folder, node)
        return node
    return None

def getRemoteNode(folder):
    results = session.get(API_ORIGIN + '/api/v2/user/slushpupie!urlpathlookup?urlpath=/' + folder,
            headers={'Accept': 'application/json'}).json()

    if results['Response']['Locator'] == 'Folder':
        node = {'id': nodeObj['Response']['Node']['NodeID'],
             'uri': nodeObj['Response']['Node']['Uri'],
             'type': nodeObj['Response']['Node']['Type']}
    elif results['Response']['Locator'] == 'Album':
        node = {'id': nodeObj['Response']['Node']['NodeID'],
             'uri': nodeObj['Response']['Node']['Uri'],
             'type': nodeObj['Response']['Node']['Type'],
             'key': nodeObj['Response']['Album']['AlbumKey']}
    else:
        node = None

    return node

def saveLocalNode(folder,node):
    with open(folder + '/.sm_node', 'w') as fh:
        fh.write(yaml.dump(config))

def getLocalNode(folder):
    with open(folder + '/.sm_node', 'r') as fh:
        return = yaml.load(fh)
    except IOError as e:
        return None

if __name__ == '__main__':
    main()
