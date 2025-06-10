import logging
import os
from datetime import datetime
from dotenv import load_dotenv
import base64

# Load environment variables from .env
load_dotenv()

# Configuration from environment variables
API_BASE_URL = os.getenv("API_BASE_URL", "https://ls-app-airt.csir.co.za")
API_KEY = os.getenv("API_KEY")
TANDEM_WEBHOOK_URL = os.getenv("TANDEM_WEBHOOK_URL")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", 300))  # Default: 5 minutes
USER_ID = os.getenv("USER_ID", "default")


# Use room name based on your facility
ROOM_NAME = 'OFFICE E-102'
# Use classification id based on your facility template
CLASSIFICATION_ID = '3d'

def main():
    # Start
    # STEP 1 - obtain token. The sample uses 2-legged token but it would also work
    # with 3-legged token assuming that user has access to the facility
    token = create_token(APS_CLIENT_ID, APS_CLIENT_SECRET, ['data:read', 'data:write'])
    with TandemClient(lambda: token) as client:
        # STEP 2 - get facility and default model.
        facility = client.get_facility(FACILITY_URN)
        default_model = get_default_model(FACILITY_URN, facility)
        if default_model is None:
            print('Unable to find default model')
            return
        # STEP 3 - find room by name. We assume there is only one room with given name.
        room_name = ROOM_NAME
        uniformat_class_id = 'D7070' # this refers to Electronic Monitoring and Control
        category_id = 5031 # this refers to IoT Connections category
        classification = CLASSIFICATION_ID
        # iterate through rooms
        for l in facility.get('links'):
            model_id = l.get('modelId')
            # we need to query for refs because we want to know related level
            rooms = client.get_rooms(model_id, [ COLUMN_FAMILIES_STANDARD, COLUMN_FAMILIES_REFS ])
            room = next((r for r in rooms if r.get(QC_NAME) == room_name), None)
            if room is not None:
                target_room = room
                target_room_model_id = model_id.replace('urn:adsk.dtm:', '')
                break
        if target_room is None:
            print(f'Room {room_name} not found')
            return
        # STEP 4 - find level. Level with same name should exist in default model.
        level_details = client.get_element(target_room_model_id, target_room.get(QC_LEVEL))
        levels = client.get_levels(default_model.get('modelId'))
        target_level = next((l for l in levels if l.get(QC_NAME) == level_details.get(QC_NAME)), None)

        if target_level is None:
            print(f'Level {level_details.get(QC_NAME, None)} not found')
            return
        # STEP 5 - create new stream. First step is to encode keys for references. In our case host element and room are same.
        target_room_key = to_full_key(target_room.get(QC_KEY))
        parent_xref = to_xref_key(target_room_model_id, target_room_key)
        # create new stream
        stream_id = client.create_stream(
            default_model.get('modelId'),
            room_name,
            uniformat_class_id,
            category_id,
            classification,
            parent_xref, # because stream is assigned to room we use same key for host & room
            parent_xref,
            target_level.get(QC_KEY))
        print(f'New stream: {stream_id}')
        # STEP 6 - reset stream secrets
        client.reset_stream_secrets(default_model.get('modelId'), [ stream_id ])
        # to push data to stream follow other stream examples


if __name__ == '__main__':
    main()
