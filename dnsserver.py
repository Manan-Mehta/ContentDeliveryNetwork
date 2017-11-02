#! /usr/bin/python

import socket
import re
import sys
from struct import *
import threading
import math
import urllib2,urllib

# Replica Servers
# ec2-54-210-1-206.compute-1.amazonaws.com                N. Virginia
# ec2-54-67-25-76.us-west-1.compute.amazonaws.com         N. California
# ec2-35-161-203-105.us-west-2.compute.amazonaws.com      Oregon
# ec2-52-213-13-179.eu-west-1.compute.amazonaws.com       Ireland
# ec2-52-196-161-198.ap-northeast-1.compute.amazonaws.com Tokyo
# ec2-54-255-148-115.ap-southeast-1.compute.amazonaws.com Singapore
# ec2-13-54-30-86.ap-southeast-2.compute.amazonaws.com    Sydney
# ec2-52-67-177-90.sa-east-1.compute.amazonaws.com        Sao Paolo
# ec2-35-156-54-135.eu-central-1.compute.amazonaws.com    Frankfurt

#list of all replica server
replicaCDNs=("ec2-54-210-1-206.compute-1.amazonaws.com",
"ec2-54-67-25-76.us-west-1.compute.amazonaws.com",
"ec2-35-161-203-105.us-west-2.compute.amazonaws.com",
"ec2-52-213-13-179.eu-west-1.compute.amazonaws.com",
"ec2-52-196-161-198.ap-northeast-1.compute.amazonaws.com",
"ec2-54-255-148-115.ap-southeast-1.compute.amazonaws.com",
"ec2-13-54-30-86.ap-southeast-2.compute.amazonaws.com",
"ec2-52-67-177-90.sa-east-1.compute.amazonaws.com",
"ec2-35-156-54-135.eu-central-1.compute.amazonaws.com")

replicaIPs = [
          '54.210.1.206',
          '54.67.25.76',
          '35.161.203.105',
          '52.213.13.179',
          '52.196.161.198',
          '54.255.148.115',
          '13.54.30.86',
          '52.67.177.90',
          '35.156.54.135'
          ]

#RTTips = {}

# Geo location of all replica servers
GeoreplicaIPs =  {
            '54.210.1.206'  : (39.0437,-77.4875),
            '54.67.25.76'   : (37.3394,-121.895),
            '35.161.203.105': (45.8696,-119.688),
            '52.213.13.179' : (53.3331,-6.2489),
            '52.196.161.198': (35.685,139.7514),
            '54.255.148.115': (1.2931,103.8558),
            '13.54.30.86'   : (41.1271,-73.4416),
            '52.67.177.90'  : (-23.4733,-46.6658),
            '35.156.54.135' : (42.2734,-83.7133)
            }



# Check if inputs were correct
if len(sys.argv) != 5 or sys.argv[1] != "-p" or sys.argv[3] != "-n":
    print "Arguments given wrong"
    exit()

# Get CDN specific name to be translated to IP
CDNname = sys.argv[4]
# Get DNS port number and check if it is in the right range
DNSport = int(sys.argv[2])
if DNSport < 40000 and DNSport > 65535:
    print "Port Number in wrong range"
    exit()

# Give a different port to run thread to find RTT
if DNSport == 40000:
    RttPort = DNSport+1
else:
    RttPort = DNSport-1


class BestReplica:
    
    def __init__(self):
        self = self
        #closestIP = None

    # Through Geolocation, find closest server
    def getGeoDist(self,Cip):
        if Cip in replicaIPs:
            # client is run from one of the replica servers itself
            closestIP = Cip
            return closestIP

        else:
            # Calculate client's distance from Replica servers and get closest replica server
            dist = {}
            locURL = "http://ip-api.com/json/"+Cip
            latlon = urllib2.urlopen(locURL).read()
            Clat = float(re.findall('"lat":([+-]?\d+\.\d+)',latlon)[0])
            Clon = float(re.findall('"lon":([+-]?\d+\.\d+)',latlon)[0])
            # Find distance between replica servers and Client
            for rip,rloc in GeoreplicaIPs.items():
                Rlat = rloc[0]
                Rlon = rloc[1]
                lon1 = (90.0 - Clat) * math.pi/180.0
                lon2 = (90.0 - Rlat) * math.pi/180.0
                n1 = Rlon * math.pi/180.0
                n2 = Clon * math.pi/180.0
                c = (math.sin(lon1) * math.sin(lon2) * math.cos(n1 - n2) + math.cos(lon1) * math.cos(lon2))
                d = math.acos(c)

                dist[d] = rip

            closestIP = dist[min(dist)]
            return closestIP


    # Send HTTP request to HTTPserver asking it to give back the RTT taken
    def getRTTarray(self,Rip,Cip,RTTips):
        httpquery = "http://" + str(Rip) +':'+str(RttPort)+"/" + Cip
        rttvalue = urllib2.urlopen(httpquery).read()

        try:
            RTTips[float(rttvalue)] = Rip       # Key:values of RTT:replica IP
        except:
            RTTips[50.0] = Rip


    def getMinRTT(self,Cip):
        RepThreads = []
        RTTips = {}

        if Cip in replicaIPs:
            # client is run from one of the replica servers itself
            closestIP = Cip
            return closestIP

        GeobestIP = self.getGeoDist(Cip)

        for Rip in replicaIPs:
            th = threading.Thread(target=self.getRTTarray, args=(Rip, Cip,RTTips))
            th.daemon = True
            th.start()
            RepThreads.append(th)   # Add the all replica threads to thread list
        # Wait for all threads to complete
        for th in RepThreads:
            th.join()

        BestRIP = RTTips[min(RTTips.keys())]

        if BestRIP > 49.0:
            BestRIP = GeobestIP

        return BestRIP

    # Extract DNS
    def getDomain(self,DNSsoc,DNSquery,SendrIP):
        Cip = str(SendrIP[0])

        DNSQHeader = unpack('!HHHHHH', DNSquery[0:12])
        DNSQquestion = DNSquery[12:]
        next_len =  unpack('!B', DNSQquestion[0])[0]

        length = 0
        domain = ""

        # From the question extract the Domain name which needs to be resolved
        while (next_len != 0):
            length = length + 1
            tot_len = length + next_len
            domain += unpack('!'+ str(next_len) + 's', DNSQquestion[length:tot_len])[0]+"."
            next_len = unpack('!B', DNSQquestion[tot_len])[0]
            length = tot_len

        domain = domain.rstrip(".")

        # Get parameters: type and class
        DNSQtype = unpack('!H', DNSQquestion[tot_len+1:tot_len+3])[0]
        DNSQclass = unpack('!H', DNSQquestion[tot_len+3:tot_len+5])[0]
        #return domain

    #def sendDNSResponse(Cip,domain):
        DNSQresp= ""
        sIP = self.getMinRTT(Cip)
        BestSIP = socket.inet_aton(sIP)

        if domain == CDNname:
        # If received domain name and CDN specific name given in argument is same, create and send response packet
            DNSQresp+= pack('!H', DNSQHeader[0]) + "\x81\x80"                     # Same as DNS query header
            DNSQresp+= pack('!HHHH', 1,1,0,0)                                     # 1 Question, 1 Answer, NOT Authoritative, no additional Answers
            DNSQresp+=DNSquery[12:12+tot_len+5]                                   # Original Domain Name Question
            DNSQresp+='\xc0\x0c'                                                  # Query Response - Pointer to domain name
            DNSQresp+= pack('!HHLH4s', DNSQtype, DNSQclass, 60,4,BestSIP)         # Query Response - Response type,class,ttl,resource data length,IP address

        else:
            # Else No record found response
            DNSQresp+= pack('!H', DNSQHeader[0]) + "\x81\x83"                # Same as DNS query header
            DNSQresp+= pack('!HHHH', 1,1,0,0)                                # 1 Question and 1 Answer
            DNSQresp+=DNSquery[12:12+tot_len+5]                              # Original Domain Name Question

        # Send DNS Response
        DNSsoc.sendto(DNSQresp, SendrIP)
        # print "DNS Response sent"


def DNSQueryH(DNSsoc,DNSquery,SendrIP):
    var = BestReplica()
    var.getDomain(DNSsoc,DNSquery,SendrIP)


# Bind DNS socket (using UDP) to port specified in the argument
try:
    DNSsoc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)       # UDP socket
    DNSsoc.bind(('', DNSport))
except:
    print "Socket could not be created"
    exit()

# Find RTTs as the main process

while True:
    # Receive DNS query
    DNSquery,SendrIP = DNSsoc.recvfrom(1024)

    # Unpack DNS Query headers to extract question later
    th1 = threading.Thread(target=DNSQueryH, args=(DNSsoc,DNSquery,SendrIP))
    th1.daemon = True
    th1.start()

