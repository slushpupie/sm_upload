#!/usr/bin/env python

#from rauth import OAuth1Session
import requests
import logging
#from requests_oauthlib import OAuth1Session

import sys, os

import argparse

from common import SmugMugSession

from urllib import urlencode, quote, quote_plus

import pprint

import yaml, json
pp = pprint.PrettyPrinter(indent=4)

# These two lines enable debugging at httplib level (requests->urllib3->http.client)
# You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# The only thing missing will be the response.body which is not logged.
# try:
#     import http.client as http_client
# except ImportError:
#     # Python 2
#     import httplib as http_client
# http_client.HTTPConnection.debuglevel = 1

# You must initialize logging, otherwise you'll not see debug output.
# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

API_ORIGIN = SmugMugSession.API_ORIGIN
known_types = [".jpg", ".jpeg", ".gif", ".png"]
#session

def main(dryrun):
    """This example interacts with its user through the console, but it is
    similar in principle to the way any non-web-based application can obtain an
    OAuth authorization from a user."""
    global session
    sm_session = SmugMugSession()
    session = sm_session.get_session()

    print "Getting local root node"
    node = getLocalNode('')
    if not node:
        #userObj = session.get(API_ORIGIN + '/api/v2/user/slushpupie',
        #        headers={'Accept': 'application/json'}).json()
        #nodeUri = userObj['Response']['User']['Uris']['Node']['Uri']
        print "Getting remote root node"
        node = getRemoteNode('')
        print "Saving local node"
        saveLocalNode('.',node)

    for root, dirs, files in os.walk('Photos'):
        # Strip off the 'Photos/' part of the root path
        r = root[6:]
        print "Getting node for '%s'" % (r)
        node = getNode(r)
        if not node:
            if len(files) > 0 and len(dirs) > 0:
                print "You cant have directories with Images and Folders (%s)" % root
            elif len(files) > 0:
                if dryrun:
                    print "Would create album %s, but in dryrun mode" % (r)
                else:
                    create_album(r)
            elif len(dirs) > 0:
                if dryrun:
                    print "Would create folder %s, but in dryrun mode" % (r)
                else:
                    create_folder(r)
            else:
                print "Skipping empty directory "+r

        for f in files:
            _ignore, ext = os.path.splitext(f)
            if ext.lower() in known_types:

                if not image_exist(r,f):
                    if dryrun:
                        print "Would upload image %s into %s, but in dryrun mode" % (f,r)
                    else:
                        if not image_upload(r,f):
                            print "Error uploading"


def image_upload(folder,image_name):
    global session

    node = getNode(folder)
    if not node:
        print "Folder %s not registered in SmugMug yet, what happened?" % (folder)
        return False

    file = {'file': open('Photos/'+folder+'/'+image_name, 'rb')}
    print "Uploading %s into %s (%s)" % (image_name, folder, node['key'])
    response = session.post('http://upload.smugmug.com/',
        headers={'X-Smug-AlbumUri': '/api/v2/album/%s' % (node['key']),
              'X-Smug-ResponseType': 'JSON',
              'X-Smug-Version': 'v2',
              'X-Smug-FileName': image_name},
        files=file).json()
    if response['stat'] == 'ok':
        image_exist(folder,image_name)
        return True
    print "Error on upload"
    pp.pprint(response)

def image_exist(folder,image_name):
    global session
    node = getNode(folder)

    if not node:
        print "Folder %s not registered in SmugMug yet, what happened?" % (folder)
        return False

    if 'images' in node and node['images'] and node['images'].get(image_name, False):
        return True

    next_page = '/api/v2/album/%s!images?start=1&count=100' % (node['key'])
    while next_page:
        page = session.get(API_ORIGIN + next_page,
            headers={'Accept': 'application/json'}).json()

        if 'Pages' not in page['Response']:
            return False
        next_page = page['Response']['Pages'].get('NextPage', None)
        images = page['Response']['AlbumImage']
        for image in images:
            if image['FileName'] == image_name:
                i = {
                    'key': image['ImageKey'],
                    'uri': image['Uri']
                }
                node['images'][image_name] = i
                saveLocalNode(folder,node)
                return True

    return False

def parent(folder):
    if not folder:
        return ''
    return '/'.join(folder.split('/')[:-1])

def base_name(folder):
    if not folder:
        return ''
    return folder.split('/')[-1]

def create_folder(folder):
    global session


    if not folder:
        return False

    node = getNode(folder)
    if node:
        return node

    fname = base_name(folder)
    pnode = create_folder(parent(folder))
    if pnode:
        print "Would create folder %s in node %s (%s)" % ( fname, pnode['id'], folder )

        response = session.post(API_ORIGIN + "/api/v2/node/%s!children" % (pnode['id']),
            headers={'Accept': 'application/json',
                  'Content-Type': 'application/json'},
            data=json.dumps({'Type': 'Folder', 'Name': fname, 'UrlName': fname})).json()

        if response['Response']['EndpointType'] == 'Node':
            node = { 'id': response['Response']['Node']['NodeID'],
                  'type': 'Folder'}
            saveLocalNode(folder,node)
            return node

    print "Something went wrong; cant create folder-node %s" % (folder)
    return False






def create_album(folder):
    global session

    if not folder:
        return False

    node = getNode(folder)
    if node and node['Type'] == 'Album':
        return node
    if node:
        print "%s was already created, but not as an Album. Cannot convert"
        return False


    fname = base_name(folder)
    pnode = create_folder(parent(folder))
    if pnode:
        print "Would create album %s in node %s (%s)" % ( fname, pnode['id'], folder )

        response = session.post(API_ORIGIN + "/api/v2/node/%s!children" % (pnode['id']),
            headers={'Accept': 'application/json',
                  'Content-Type': 'application/json'},
            data=json.dumps({'Type': 'Album', 'Name': fname, 'UrlName': fname})).json()

        if response['Response']['EndpointType'] == 'Node':
            node = { 'id': response['Response']['Node']['NodeID'],
                  'type': 'Album',
                  'key': base_name(response['Response']['Node']['Uris']['Album']['Uri']),
                  'images': {}}
            saveLocalNode(folder,node)
            return node

    print "Something went wrong; cant create album-node %s" % (folder)
    return False


def getNode(folder):
    if folder == "":
        folder = "/"
    node = getLocalNode(folder)
    if node:
        return node

    node = getRemoteNode(folder)
    if node:
        saveLocalNode(folder, node)
        return node
    return None

def getRemoteNode(folder):
    global session

    results = session.get('%s/api/v2/user/slushpupie!urlpathlookup?urlpath=%s' % (API_ORIGIN, quote_plus(folder)),
        headers={'Accept': 'application/json'}).json()

    #pp.pprint(results)
    if results['Response']['Locator'] == 'Folder':
        node = {'id': results['Response']['Folder']['NodeID'],
             'type': 'Folder'}
    elif results['Response']['Locator'] == 'Album':
        node = {'id': results['Response']['Album']['NodeID'],
             'type': 'Album',
             'key': results['Response']['Album']['AlbumKey'],
             'images': {}}
    else:
        node = None

    return node

def saveLocalNode(folder,node):
    with open('Photos/' + folder + '/.sm_node', 'w') as fh:
        fh.write(yaml.dump(node, default_flow_style=False))

def getLocalNode(folder):
    try:
        with open('Photos/' + folder + '/.sm_node', 'r') as fh:
            return yaml.load(fh)
    except IOError as e:
        return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run','-n', dest='dryrun', action='store_true')
    args = parser.parse_args()
    main(args.dryrun)
