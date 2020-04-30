
#########################################################################################
import greengrasssdk
import logging
import os
import signal
import sys
import json
import subprocess
import glob

from bt_manager import BTManager

node_id = os.getenv('AWS_IOT_THING_NAME') or 'NO_THING_NAME'
FW_LOADER_START_REQ_TOPIC = os.getenv('FW_LOADER_START_REQ_TOPIC') or "fwloader/trigger/{}".format(node_id)
FW_LOADER_STATUS = os.getenv('FW_LOADER_STATUS') or 'fwloader/status/{}'.format(node_id)
FW_LOADER_DEVICE = os.getenv('FW_LOADER_DEVICE') or '/dev/ttyS2'
FW_LOADER_BAUDRATE = os.getenv('FW_LOADER_BAUDRATE') or '115200'
FW_LOADER_EXE = 'btpa_firmware_loader.py'

fwload_complete = False
update_underway = False
def status_update(update): 
    resp = {"status": update}
    client.publish(topic = FW_LOADER_STATUS, payload = json.dumps(resp))

def load_firmware(file):
    global fwload_complete
    global update_underway 
    logging.info('Loading firmware file: {}'.format(file))
    res = subprocess.run([FW_LOADER_EXE, FW_LOADER_DEVICE, FW_LOADER_BAUDRATE, file, "IG60"])
    fwload_complete = True
    update_underway = False
    # Publish upload complete indication
    if res.returncode == 0:
        status_update("update complete result {}".format(res.returncode))
        with BTManager(FW_LOADER_DEVICE) as bt: 
            hex = bt.get_sb_hex()
            status_update("hex version {}".format(hex.decode("ascii")))

    else: 
        status_update("update failed result {}".format(res.returncode))
        logging.error(res.stderr)


def function_handler(event, context):
    global update_underway
    try: 
        topic = context.client_context.custom['subject']
        logging.info("handle event {} ".format(topic))
        if topic == FW_LOADER_START_REQ_TOPIC:
            update_file = event['update-file']
            files = glob.glob('*.uwf')
            if update_file not in files:
                logging.error("update file {} not found".format(update_file)) 
                return 
        
            if not update_underway:
                update_underway = True
                logging.info('Received startup indication; starting firmware load.')
                status_update("update triggered")
                load_firmware(update_file)
        else: 
            logging.info("topic not supported  {} ".format(topic))
    
    except Exception as e: 
        logging.error("unable to parse topic")
        logging.error(e)



# Set up logging
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

# Create a greengrass core sdk client
client = greengrasssdk.client('iot-data')
status_update("firmware update ready to run ")
logging.info("firmware update lambda ready to run ")
