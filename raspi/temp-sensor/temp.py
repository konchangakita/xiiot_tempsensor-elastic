##########################################################################
# Filename    : temp.py
# Description : xi-iot temp senssor ith OSOYOO DHT11 humiture & temperature module
##########################################################################
import RPi.GPIO as GPIO
import time
import paho.mqtt.client as mqtt
import os
import json
import argparse
parser = argparse.ArgumentParser()

#DHT11 connect to BCM_GPIO14
DHTPIN = 14

GPIO.setmode(GPIO.BCM)

MAX_UNCHANGE_COUNT = 100

STATE_INIT_PULL_DOWN = 1
STATE_INIT_PULL_UP = 2
STATE_DATA_FIRST_PULL_DOWN = 3
STATE_DATA_PULL_UP = 4
STATE_DATA_PULL_DOWN = 5

# Setting for Xi IoT Edge OS
EDGE_SERVER = os.getenv('EDGE_SERVER','192.168.199.99')
EDGE_PORT = os.getenv('EDGE_PORT',1883)
temp_data = {}

# Setting for payload
LOCATION = 'tokyo'

# if set parser overwrite
parser.add_argument('-l', '--location')
args = parser.parse_args()
LOCATION = args.location if args.location else LOCATION


def read_dht11_dat():
    GPIO.setup(DHTPIN, GPIO.OUT)
    GPIO.output(DHTPIN, GPIO.HIGH)
    time.sleep(0.05)
    GPIO.output(DHTPIN, GPIO.LOW)
    time.sleep(0.02)
    GPIO.setup(DHTPIN, GPIO.IN, GPIO.PUD_UP)

    unchanged_count = 0
    last = -1
    data = []
    while True:
        current = GPIO.input(DHTPIN)
        data.append(current)
        if last != current:
            unchanged_count = 0
            last = current
        else:
            unchanged_count += 1
            if unchanged_count > MAX_UNCHANGE_COUNT:
                break

    state = STATE_INIT_PULL_DOWN

    lengths = []
    current_length = 0

    for current in data:
        current_length += 1

        if state == STATE_INIT_PULL_DOWN:
            if current == GPIO.LOW:
                state = STATE_INIT_PULL_UP
            else:
                continue
        if state == STATE_INIT_PULL_UP:
            if current == GPIO.HIGH:
                state = STATE_DATA_FIRST_PULL_DOWN
            else:
                continue
        if state == STATE_DATA_FIRST_PULL_DOWN:
            if current == GPIO.LOW:
                state = STATE_DATA_PULL_UP
            else:
                continue
        if state == STATE_DATA_PULL_UP:
            if current == GPIO.HIGH:
                current_length = 0
                state = STATE_DATA_PULL_DOWN
            else:
                continue
        if state == STATE_DATA_PULL_DOWN:
            if current == GPIO.LOW:
                lengths.append(current_length)
                state = STATE_DATA_PULL_UP
            else:
                continue
    if len(lengths) != 40:
        print("Data not good, skip")
        return False

    shortest_pull_up = min(lengths)
    longest_pull_up = max(lengths)
    halfway = (longest_pull_up + shortest_pull_up) / 2
    bits = []
    the_bytes = []
    byte = 0

    for length in lengths:
        bit = 0
        if length > halfway:
            bit = 1
        bits.append(bit)
    #print("bits: %s, length: %d" % (bits, len(bits)))
    for i in range(0, len(bits)):
        byte = byte << 1
        if (bits[i]):
            byte = byte | 1
        else:
            byte = byte | 0
        if ((i + 1) % 8 == 0):
            the_bytes.append(byte)
            byte = 0
    print(the_bytes)
    checksum = (the_bytes[0] + the_bytes[1] + the_bytes[2] + the_bytes[3]) & 0xFF
    if the_bytes[4] != checksum:
        print("Data not good, skip")
        return False

    return the_bytes[0], the_bytes[2]

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("temp-sensor")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" - "+str(msg.payload))

def main():
    print("Raspberry Pi wiringPi DHT11 Temperature test program\n")
    while True:
        result = read_dht11_dat()
        if result:
            humidity, temperature = result
            print("humidity: %s %%,  Temperature: %s °C, Location: %s" % (humidity, temperature, LOCATION))
            
            #mqtt publish
            temp_data["temperature"] = temperature
            temp_data["humidity"] = humidity
            temp_data["location"] = LOCATION
            mqclient.publish("data/temp", json.dumps(temp_data))

        time.sleep(1)

def destroy():
    GPIO.cleanup()


#launch MQTT subsystem
mqclient = mqtt.Client()
mqclient.on_connect = on_connect
mqclient.on_message = on_message
#mqclient.message_callback_add("factory/motor", on_motor)

mqclient.tls_set(ca_certs="mqtt-cert/CACertificate.crt", certfile="mqtt-cert/certificate.crt", keyfile="mqtt-cert/privateKey.key")
mqclient.tls_insecure_set(True)

mqclient.connect(EDGE_SERVER, EDGE_PORT, 60)
mqclient.loop_start()



if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        destroy() 

