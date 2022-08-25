import json
import copy
import uuid
from os.path import dirname, join

from invenio_db import db
from invenio_pidstore import current_pidstore
from invenio_records import Record
from weko_records.api import ItemsMetadata, WekoRecord
from weko_deposit.pidstore import weko_deposit_minter
from invenio_pidstore.models import PersistentIdentifier, PIDStatus, Redirect
from weko_deposit.api import WekoDeposit

def json_data(filename):
    with open(join(dirname(__file__),filename), "r") as f:
        return json.load(f)


def create_record(record_data, item_data):
    """Create a test record."""
    with db.session.begin_nested():
        record_data = copy.deepcopy(record_data)
        item_data = copy.deepcopy(item_data)
        rec_uuid = uuid.uuid4()

        # dep = WekoDeposit.create(record_data,recid=record_data["recid"])
        # dep.commit()
        
        PersistentIdentifier.create('recid', record_data["recid"],object_type='rec', object_uuid=rec_uuid,status=PIDStatus.REGISTERED)
        depid = PersistentIdentifier.create('depid', record_data["recid"],object_type='rec', object_uuid=rec_uuid,status=PIDStatus.REGISTERED)
        if '.' in record_data["recid"]:
            PersistentIdentifier.create('parent', "parent:{}".format(record_data["recid"]),object_type='rec', object_uuid=rec_uuid,status=PIDStatus.REGISTERED)
        record = WekoRecord.create(record_data, id_=rec_uuid)
        item = ItemsMetadata.create(item_data, id_=rec_uuid)
        print(record_data['_buckets']['deposit'])
    return depid, record, item
