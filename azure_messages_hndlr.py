import json
import sys
from azure.iot.hub import IoTHubRegistryManager

CONNECTION_STRING = "HostName=OTADeviceHub.azure-devices.net;SharedAccessKeyName=service;SharedAccessKey=HDJ7yFLBC4y6bFvQuWl1yy1M43Z7QkDKB2RyZwdrUXk="
DEVICE_ID = "OTAmaster"

def send_request_messagses(data,messageType):
    try:
        # Create IoTHubRegistryManager
        registry_manager = IoTHubRegistryManager(CONNECTION_STRING)

        props={}
        # optional: assign system properties
        props.update(messageId = messageType)

        props.update(contentType = "application/json")

        registry_manager.send_c2d_message(DEVICE_ID, data, properties=props)

    except Exception as ex:
        print ( "Unexpected error" )
        return



