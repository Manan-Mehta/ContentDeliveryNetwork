ReadMe
High Level Approach
1.	Active Measurements (ping)
•	We have used active measurements to calculate the RTT so as to locate the nearest replica server. 
•	The RTT is calculated using ping command. 
•	We are using dictionary that will keep record of the server to rtt_value mapping and will select the replica server with least RTT
•	The DNS server will send a request to HTTP server with client IP, which will do ping command to the client IP and return the value of RTT in response.
2.	Passive Measurements using Geolocation were done to find the nearest HTTP Server.
•	The geolocation of the client is compared with the replica server geographic location.
•	The closest replica server to the client based on the latitude and longitude is calculated by the DNS server and then returned to client.
3.	Caching Mechanism
•	We are creating a file named Cache on the HTTP servers to store the pages that are downloaded from the origin server.
•	When the httpserver receives a request regarding any page it will first check its cache memory i.e it will check the cache file. 
i.	In case the entry is present it will increase hit counter and send the page to the client
ii.	In case there is no entry, then it will create a new entry in the cache file. It will send the request to the origin sever and get the data. The data is saved in cache and sent to client.
•	If the cache file is full, then it will remove the entry which has least number of visits and is least popular. 
•	The mechanism tracks the least and most popular and keeps the cache updated.
For choosing best replica server:
•	 Geolocation and RTT are done and if ping works well, IP given by RTT is given highest priority.

Working:
•	For CDN
1.	First the deployCDN will be run. This scripts will copy the DNS script on cs5700cdnproject.ccs.neu.edu server and HTTP scripts on all the replica servers.
2.	Then we execute the runCDN script which will SSH into the respective server and give executable permissions to the scripts. This script will also run the dnsserver and httpserver scripts in the background i.e it will store DNS and replica
3.	Client will send query to DNS server to get best replica server IP.
4.	Now the DNS after receiving the query will validate the domain name and then perform the active and passive measurements to locate the best replica server i.e) with lowest RTT or which one is closest to the client.
5.	The DNS server will create a response packet along with the best replica server and send it back to the client. 
6.	The client will then query that replica server. The replica server will check if it has the requested data in its own database. 
7.	If the data is present it will increase the hit counter and take the data from its cache and send it back to the client.
8.	If the data is not present in the cache, the replica server will forward the request to the origin server and obtain the data. The replica server will then add the new entry for this data in its cache and send the data to the client. 
9.	In the end the stopCDN scripts are run which will halt the dnsserver and httpservers.

•	DNS server 
1.	The DNS server will first check for arguments. The DNS server will first create an UDP socket and bind it to port number specified in the command line argument. 
2.	We have used threading in DNS server so that it can handle multiple clients at the same time. When the DNS receives a request it will open a separate thread to analyze the specific request. 
3.	When it receives a request it will call the function that will look for the replica server with lowest latency. We have specified a list that contains the IP of all the replica servers and we have one more dictionary to store the mapping between server along with its rtt value. 
4.	For each replica server, the function will first check if rtt value by opening another thread to send a request to httpserver to get the rtt value after using ping tool.
5.	Before getting the replica server IP address, the server will verify the domain name. If it is not correct it will send an NXDOMAIN error code in the response. Else it will create a response packet along with the replica server IP address in the answer section of the DNS packet.
6.	Once the response is packed it will send through UDP socket back to the client.

•	HTTP server 
1.	The http server will first verify the command line arguments i.e. the port number and the origin server name. The http server will create a TCP socket and bind it to the port mentioned.
2.	We have used multi-threading in httpserver. One thread is to handle requests from clients, second to manage cache, and third to serve RTT requests from DNS server.
3.	When HTTP will receive a request from the client it will search in its cache file whether the request is cached or not.
4.	If the request is in the cache, then the httpserver will extract the data from the cache file and respond the client. 
5.	If the request is not cached, then the http server will create a new entry in the data base and forward the client query to the origin server mentioned in the command line argument. The origin server sends back the data requested to the replica server. 
6.	The http server receives the data from origin server and stores it in the cache and then responds to the client.
7.	 In case, the entry is not cached and the cache file is full then the server discards the least popular entry from the database to store the new one. 
8.	Limit of cache size is 10MB. The cache will never exceed this size.
9.	If the validation is correct then function run the ping in the format - "ping -c 1 [client ip]” is done. 
    From this the function extracts the rtt and sends it back to the dns server in response.

•	deployCDN script - 
-	This is a bash script that contains commands to copy the dnsserver and httpserver scripts to the respective servers. 
•	runCDN script –
-	This is a bash script that will ssh into the respective servers and provide executable permissions to the scripts.
•	stopCDN script -
-	This is a bash script that will ssh into the servers and stop the scripts. 

Challenges
1.	Implementing the caching mechanism and maintaining a hit count was very difficult.
2.	Working with the threading 
3.	Understanding and implementing the active mechanism was a challenge

Testing

1.	To run the CDN:./[deploy|run|stop]CDN -p <port> -o <origin> -n <name> -u <username> -i <keyfile>
2.	The dnsserver was tested using the dig command - 
 	format - dig @[DNS server ip address] -p <port number> <domain name>
3.	The httpserver was tested using the wget command with server as taken from DNS server response-
 	format - wget http://[server ip]:[port number]/<path to content>

