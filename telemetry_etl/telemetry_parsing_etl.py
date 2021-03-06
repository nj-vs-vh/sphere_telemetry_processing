"""Module for parsing telemetry data from logs and storing in local MongoDB"""

from pymongo import MongoClient
import numpy as np
import pandas as pd

from tqdm import tqdm

from sphere_log_parser import yield_log_records_as_dicts

# assuming Mongo is running as mongod process/service and listening on localhost port 27017
# for installation see https://docs.mongodb.com/manual/administration/install-community/
# for restoring data from dump see README.md
client = MongoClient()
ground_telemetry_collection = client.sphere_telemetry.from_ground_logs


log_filenames = [
    'log_ground_2012.03.12_to_2012.03.14.txt',
    'log_ground_2012.03.14_to_2013.03.11.txt',
    'log_ground_2012.03.15.txt',
]

# store log filenames with ids (used as foreign key)
log_filenames_collection = client.sphere_telemetry.gound_log_filenames
for id_, log_filename in enumerate(log_filenames):
    log_filenames_collection.update_one(
        filter={'id': id_},
        update={"$set": {'id': id_, 'filename': log_filename}},
        upsert=True,
    )

for log_filename in log_filenames:
    log_path = f'data/logs_2012_complete/{log_filename}'
    print(f'loading {log_path}...')

    log_filename_id = log_filenames_collection.find_one({'filename': log_filename})['id']

    for record in tqdm(yield_log_records_as_dicts(log_path)):
        try:
            dt = pd.to_datetime(record.pop('datetime'))
        except KeyError:
            continue

        record['local_dt'] = dt

        try:
            ground_telemetry_collection.update_one(
                filter={"local_dt": {"$eq": dt}},
                update={
                    "$setOnInsert": {key: val for key, val in record.items() if val not in {np.NaN, -1}},
                    "$set": {'source_id': log_filename_id},
                },
                upsert=True
            )
        except ValueError:
            continue
