#!/bin/python3

from xml.dom import minidom
from urllib.parse import urlparse, unquote
import os, sys
import requests
import argparse
import time

try:
    from gi.repository import GLib
    PICTURES_DIR = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)
except Exception as e:
    print('Note: no GLib module available to get user\'s picture folder path. Using English folder name "Pictures".')
    from pathlib import Path
    PICTURES_DIR = str(Path.home()) + '/Pictures'

try:
    import gi; gi.require_version('Notify', '0.7')
    from gi.repository import Notify
    Notify.init('ImagingEdge4Linux')
except Exception as e:
    print('Note: no support for desktop notifications available:', e)
    Notify = None

__author__    = 'Georg Sieber'
__copyright__ = '(c) 2024-2025'


class GetContentException(Exception):
    pass

class ImagingEdge:
    VERSION = '0.2'

    ROOT_DIR_PUSH = 'PushRoot'
    ROOT_DIR_PULL = 'PhotoRoot'

    DEFAULT_IP    = '192.168.122.1'
    DEFAULT_PORT  = '64321'

    def __init__(self, address, port, output_dir, debug, notify=False):
        self.address = address
        self.port = port
        self.output_dir = output_dir
        self.debug = debug
        self.notify = notify

        self.transferStarted = False

    def startTransferNotification(self):
        if(self.transferStarted):
            return
        else:
            self.transferStarted = True

        # display "sync started" desktop notification if notification module is available
        self.notification = None
        if(self.notify and Notify):
            self.notification = Notify.Notification.new('ImagingEdge4Linux', 'Sync running...')
            self.notification.show()

    def endTransferNotification(self):
        if(not self.transferStarted):
            return
        else:
            self.transferStarted = False

        # update desktop notification to "sync finished"
        if(self.notify and self.notification):
            self.notification.update('ImagingEdge4Linux', 'Sync finished.')
            self.notification.show()
            self.notification = None

    def getServiceInfo(self):
        response = requests.get('http://'+self.address+':'+self.port+'/DmsDescPush.xml')
        return response.text

    def startTransfer(self):
        # display "Transferring" on the camera display (only works in push mode)
        response = requests.post(
            'http://'+self.address+':'+self.port+'/upnp/control/XPushList',
            headers = {
                'SOAPACTION': '"urn:schemas-sony-com:service:XPushList:1#X_TransferStart"',
                'Content-Type': 'text/xml; charset="utf-8"',
            },
            data = ('<?xml version="1.0" encoding= "UTF-8"?>'
                +'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
                +'<s:Body>'
                +'<u:X_TransferStart xmlns:u="urn:schemas-sony-com:service:XPushList:1"></u:X_TransferStart>'
                +'</s:Body>'
                +'</s:Envelope>')
        )
        if(self.debug):
            print('Transfer start response:', response.status_code, response.text)

    def endTransfer(self):
        # exit the "Send to smartphone" mode (only works in push mode)
        response = requests.post(
            'http://'+self.address+':'+self.port+'/upnp/control/XPushList',
            headers = {
                'SOAPACTION': '"urn:schemas-sony-com:service:XPushList:1#X_TransferEnd"',
                'Content-Type': 'text/xml; charset="utf-8"',
            },
            data = ('<?xml version="1.0" encoding= "UTF-8"?>'
                +'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
                +'<s:Body>'
                +'<u:X_TransferEnd xmlns:u="urn:schemas-sony-com:service:XPushList:1">'
                +'<ErrCode>0</ErrCode>'
                +'</u:X_TransferEnd>'
                +'</s:Body>'
                +'</s:Envelope>')
        )
        if(self.debug):
            print('Transfer end response:', response.status_code, response.text)

    # get dir contents
    def getDirectoryContent(self, dir, dirname, downloadSize=None, startingIndex=0):
        response = requests.post(
            'http://'+self.address+':'+self.port+'/upnp/control/ContentDirectory',
            headers = {
                'SOAPACTION': '"urn:schemas-upnp-org:service:ContentDirectory:1#Browse"',
                'Content-Type': 'text/xml; charset="utf-8"',
            },
            data = ('<?xml version="1.0"?>'
                +'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
                +'<s:Body>'
                +'<u:Browse xmlns:u="urn:schemas-upnp-org:service:ContentDirectory:1">'
                +'<ObjectID>'+dir+'</ObjectID>'
                +'<BrowseFlag>BrowseDirectChildren</BrowseFlag>'
                +'<Filter>*</Filter>'
                +'<StartingIndex>'+str(startingIndex)+'</StartingIndex>'
                +'<RequestedCount>9999</RequestedCount>'
                +'<SortCriteria></SortCriteria>'
                +'</u:Browse>'
                +'</s:Body>'
                +'</s:Envelope>')
        )
        if(self.debug):
            print('Dir content response:', response.status_code, response.text)
        if(response.status_code != 200):
            raise GetContentException('Failed to get dir content:', dir)

        dom = minidom.parseString(response.text)
        for element in dom.getElementsByTagName('Result'):
            # yes, no joke: there is a XML string encoded inside the <Result>, so we need to parse a second time
            if(self.debug):
                print('Dir content inner response:', element.firstChild.nodeValue)
            dom2 = minidom.parseString(element.firstChild.nodeValue)

            # yay, a container (sub directory)
            for element2 in dom2.getElementsByTagName('container'):
                dirname = element2.getElementsByTagName('dc:title')[0].firstChild.nodeValue
                print('Entering subdir:', element2.attributes['id'].value, '-', dirname)
                self.getDirectoryContent(element2.attributes['id'].value, dirname, downloadSize)

            # yay, an image (item)
            for element2 in dom2.getElementsByTagName('item'):
                # get name and download path
                filename = element2.getElementsByTagName('dc:title')[0].firstChild.nodeValue
                filepath = self.output_dir+'/'+dirname+'/'+filename
                # find the best resolution of this item
                url = None
                elements3 = element2.getElementsByTagName('res')
                if(not downloadSize):
                    lastSize = 0; lastResolution = 0
                    for element3 in elements3:
                        size = 0; resolution = 0
                        if('size' in element3.attributes):
                            size = int(element3.attributes['size'].value)
                        if('resolution' in element3.attributes):
                            resolution = element3.attributes['resolution'].value
                        if(size > lastSize):
                            url = element3.firstChild.nodeValue
                            lastSize = size
                            lastResolution = resolution
                # fallback 1: no item found with size property set, probably a RAW file, search for largest thumbnail
                if(not url):
                    searchSize = '_LRG'
                    if(downloadSize): searchSize = downloadSize
                    for element3 in elements3:
                        if('protocolInfo' in element3.attributes
                        and searchSize in element3.attributes['protocolInfo'].value):
                            url = element3.firstChild.nodeValue
                            break
                # fallback 2: use last <resolution> as this is most likely the best quality
                if(not url):
                    if(len(elements3) > 0 and elements3[-1].firstChild.nodeValue):
                        url = elements3[-1].firstChild.nodeValue
                # download the best resolution
                if(url):
                    self.downloadFile(url, filepath)
                else:
                    print('Unable to find a download candidate:', filename)

        numberReturned = int(dom.getElementsByTagName('NumberReturned')[0].firstChild.nodeValue)
        totalMatches = int(dom.getElementsByTagName('TotalMatches')[0].firstChild.nodeValue)
        if(startingIndex+numberReturned < totalMatches):
            self.getDirectoryContent(dir, dirname, downloadSize, startingIndex+numberReturned)

    def downloadFile(self, url, filepath=None):
        # fallback file name
        if(not filepath):
            filepath = self.output_dir+'/'+unquote(urlparse(url).path)
        # make dirs
        if(not os.path.isdir(os.path.dirname(filepath))):
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
        # do the download
        with requests.get(url, stream=True) as r:
            if(r.status_code != 200):
                print('Got unexpected status code:', r.status_code, url)
                return
            # get download size
            length = 0; written = 0
            if('content-length' in r.headers):
                length = int(r.headers['content-length'])
            # skip if exists and fully downloaded
            if(os.path.isfile(filepath)
            and length != 0 and length == os.stat(filepath).st_size):
                print('Skip existing file:', filepath)
                return
            # write chunks to file
            self.startTransferNotification()
            print('Downloading:', url, ' -> ', filepath)
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=16384):
                    f.write(chunk)
                    written += len(chunk)
            # check if everything received or download aborted
            if(length != written):
                # this can happen if the download was aborted
                # or if the file was deleted on SD card but the image is still in the camera internal database
                print('!! Bytes received do not match advertised content-length:', written, '<>', length)

def main():
    defaultImgDir = PICTURES_DIR + '/ImagingEdge4Linux'

    parser = argparse.ArgumentParser(epilog=__copyright__+' '+__author__+' - https://georg-sieber.de')
    parser.add_argument('-a', '--address', default=ImagingEdge.DEFAULT_IP, help='IP address of your camera')
    parser.add_argument('-p', '--port', default=ImagingEdge.DEFAULT_PORT, help='Port of your camera')
    parser.add_argument('-o', '--output-dir', default=defaultImgDir, help='Directory where to save the downloaded files')
    parser.add_argument('-s', '--download-size', default=None, help='Download a specific thumbnail size (LRG|SM|TN) - none for best/original quality')
    parser.add_argument('-d', '--daemon', action='store_true', help='Run in background and automatically copy images if camera is available')
    parser.add_argument('--debug', default=False, action='store_true', help='Show debug output')
    parser.add_argument('--version', action='store_true', help='Print version and exit')
    args = parser.parse_args()

    if(args.version):
        print(ImagingEdge.VERSION)
        sys.exit()

    ie = ImagingEdge(args.address, args.port, args.output_dir, args.debug, args.daemon)
    if(args.debug):
        print(ie.getServiceInfo())

    while True:
        try:
            ie.startTransfer()
            try:
                # user selected "Choose images on camera"
                ie.getDirectoryContent(ie.ROOT_DIR_PUSH, ie.ROOT_DIR_PUSH, args.download_size)
            except GetContentException as e:
                # user selected "Choose images on computer" (= access to all images)
                ie.getDirectoryContent(ie.ROOT_DIR_PULL, ie.ROOT_DIR_PULL, args.download_size)
            ie.endTransfer()
            ie.endTransferNotification()
        except requests.exceptions.ConnectionError as e:
            # ignore connection errors so that deamon mode keeps running
            print(e)

        if(args.daemon):
            print('Running in daemon mode, waiting for next request...')
            time.sleep(10)
        else:
            break

if(__name__ == '__main__'):
    main()
