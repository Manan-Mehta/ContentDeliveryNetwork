#! /usr/bin/python

import os
import socket
import sys
import threading
import random
import hashlib
import httplib
from SocketServer import ThreadingMixIn
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer

# Check if inputs were correct
if len(sys.argv) != 5 or sys.argv[1] != "-p" or sys.argv[3] != "-o":
    #if "-p" not in sys.argv or "-o" not in sys.argv
    print "Arguments given wrong"
    exit()

# Get port on which HTTP server is going to listen
HTTPport = int(sys.argv[2])
OriginServerName = (sys.argv[4])

#create cache directory
cacheDir = "./cache/"
if not os.path.exists(cacheDir):
    os.makedirs(cacheDir)
FHmap = {}

# Calculate the size of the cache folder
def getCacheUsedSize():
    memsiz =  os.path.getsize(cacheDir)
    for fileN in os.listdir(cacheDir):
        Npath = os.path.join(cacheDir,fileN)
        if os.path.isfile(Npath):
            memsiz += os.path.getsize(Npath)

    return memsiz

def RunUpdateCache():
    # Check the size of the cache, if it is getting closer to 10MB, delete least used file
    memsiz = getCacheUsedSize()
    if memsiz > 9999000:
        leasthit = min(FHmap.values())
        for fileN,Nhits in FHmap.items():
            if Nhits == leasthit:
                FHmap.pop(fileN)
                os.remove(cacheDir+fileN)
                

# Create a class to handle the request
class initialHandler(BaseHTTPRequestHandler):
    OriginS = None  # Origin Server Name
    HPort = None    # HTTP port
    FHmap = None    # File name to number of hits map

    #Create a class to serve HTTP request

    
class HTTPReqServH(initialHandler):
    
    def do_GET(self):
        PtoContent = hashlib.md5(self.path).hexdigest()

        # If file already present in cache, send it to client directly
        Npath = os.path.join(cacheDir,PtoContent)

        if PtoContent in self.FHmap.keys() or os.path.exists(Npath):
            filepath = open(cacheDir+PtoContent,"r+")
            self.send_response(200)
            self.end_headers()
            data = filepath.read()
            self.wfile.write(data)   # Send to client content in cache
            self.FHmap[PtoContent] = self.FHmap.get(PtoContent,0)+1     # Increase the number of hits value
            filepath.close()

        else:
	    # Get file from Origin, write it in cache and send to client
            try:
                OriginSCon = httplib.HTTPConnection(self.OriginS,8080)
                #OriginSCon.debuglevel = 1
                OriginSCon.request("GET",self.path,headers={"User-Agent":"Python httplib"})
                OriginData = OriginSCon.getresponse()
                Ostatus = OriginData.status
                self.send_response(Ostatus)
                self.end_headers()
                data = OriginData.read()
                self.wfile.write(data)
                self.FHmap[PtoContent] = self.FHmap.get(PtoContent,0)+1     # Increase the number of hits value
                filepath = open(cacheDir+PtoContent,"w+")
                filepath.write(data)
                filepath.close()
            except IOError as chk:
                print chk


class ServerHandler(HTTPServer):
    
    def serve_forever(self,OriginS,HPort,FHmap):
        # Initialize the parameters
        self.RequestHandlerClass.OriginS = OriginS
        self.RequestHandlerClass.FHmap = FHmap
        self.RequestHandlerClass.HPort = HPort
        HTTPServer.serve_forever(self)

class ThreadingServer(ThreadingMixIn,ServerHandler):
    pass

def runHTTPServer(OriginS,HPort,FHmap):
    # Run HTTP server and make it listen on the port number specified
    HServer = ThreadingServer(('', HPort),HTTPReqServH)
    HServer.serve_forever(OriginS,HPort,FHmap)


class RTTcheckH(initialHandler):
    
    # Receive RTT request
    def do_GET(self):
        try:
            hname = self.path.strip("/")
            command = "ping -c 1 " + hname + " | grep rtt"
            k1=os.popen(command).readlines()
            r = k1[0].split()[3]
            rtt = r.split("/")[1]
        except:
            # If scamper cannot return RTT then return NULL
            rtt = 50.0

        #self.send_response(200)
        #self.end_headers()
        self.wfile.write(rtt)
        

# thread for finding RTT
class RTTServerHandler(HTTPServer):
    
    def serve_forever(self, RttPort):
        self.RequestHandlerClass.HPort=RttPort
        HTTPServer.serve_forever(self)

        
# thread for finding RTT
class ThreadingRTT(ThreadingMixIn,RTTServerHandler):
    pass

def runRTTFind(RttPort):
    RttServer = ThreadingRTT(('', RttPort),RTTcheckH)
    RttServer.serve_forever(RttPort)


# Select RTT calculate server Port that it should listen on
if HTTPport == 40000:
    RttPort = HTTPport+1
else:
    RttPort = HTTPport-1

# Start the threads for HTTP server, checking cache size, RTT server
th1 = threading.Thread(target=runHTTPServer,args=(OriginServerName,HTTPport,FHmap))
th1.daemon=True
th2 = threading.Thread(target=runRTTFind ,args=(RttPort,))
th2.daemon=True
th3 = threading.Thread(target=RunUpdateCache)
th3.daemon=True

#runHTTPServer(OriginServerName,HTTPport,FHmap)
# start all threads
th1.start()
th2.start()
th3.start()

# wait for threads to complete
while 1:
    th1.join()
    th2.join()
    th3.join()

