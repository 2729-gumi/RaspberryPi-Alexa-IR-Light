# -*- coding: utf-8 -*-

import time
import sys
import os
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import pigpio
import json
import subprocess
import threading

os.chdir( os.path.dirname( os.path.abspath(__file__) ) )

# AWS IoT Core config
aws_iam_key = "XXXXXXXXXXXXXXXXXXXX"
aws_iam_secret_key = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
aws_endpoint = "xxxxxxxxxxxxxxxxxx.iot.us-west-2.amazonaws.com"
aws_region = "us-west-2"
aws_port = 443

aws_root_ca_path = "AmazonRootCA1.pem"

aws_topic_shadow = "$aws/things/RaspberryPiZero/shadow/update"
aws_topic_shadow_delta = "$aws/things/RaspberryPiZero/shadow/update/delta"


def switch_room_light (val) :
	if val :
		subprocess.call('{} irrp.py -p -g27 -f codes light:on'.format(sys.executable) , shell=True)
	else :
		subprocess.call('{} irrp.py -p -g27 -f codes light:off'.format(sys.executable) , shell=True)
	
	print( 'Room Light : {}'.format(val) )
	report_status('room-light-power', val)


# Callback Function
def callback (_, userdata, message):
	print( 'Topic:{}, Payload:{}'.format(message.topic, message.payload) )
	
	obj = json.loads( message.payload )

	#state = obj['state']
	
	if not 'desired' in obj['state'] :
		return
	state = obj['state']['desired']
	
	if 'led-power' in state :
		val = state['led-power']
		pig.write(17, val)
		print( 'LED : {}'.format(val) )
		report_status('led-power', val)

	if 'room-light-power' in state :
		try :
			if thread_room_light.is_alive() :
				return
		except UnboundLocalError :
			pass
		val = state['room-light-power']
		thread_room_light = threading.Thread(target=switch_room_light, args=(val,) )
		thread_room_light.start()


# Change Repoted Value
def report_status(name, val) :
	obj = { 'state' :
			{ 'reported' :
				{ name : val }
			}
		}
	client.publish(aws_topic_shadow, json.dumps(obj), 0)


# GPIO Initialization
pig = pigpio.pi()
pig.set_mode(17, pigpio.OUTPUT)
pig.write(17, 0)
print('GPIO Initialization Finished !')


# Connect AWS IoT Core
client = AWSIoTMQTTClient('', useWebsocket=True)
client.configureIAMCredentials(aws_iam_key, aws_iam_secret_key)
client.configureCredentials(aws_root_ca_path)
client.configureEndpoint(aws_endpoint, aws_port)
client.connect()
#client.subscribe(aws_topic_shadow_delta, 1, callback)
client.subscribe(aws_topic_shadow, 1, callback)

print('AWS IoT Core Connection & Subscription Established !')


try :
	while True :
		time.sleep(5)
except KeyboardInterrupt:
	pig.stop()
