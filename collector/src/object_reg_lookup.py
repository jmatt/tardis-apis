#!/usr/bin/python2.6

import sys
import datetime
import MySQLdb
from webob import Request
import json
import uuid
# from thrift.transport import TTransport
# from thrift.transport import TSocket
# from thrift.transport import THttpClient
# from thrift.protocol import TBinaryProtocol
# from genpy.Snowflake import Snowflake
# from genpy.Snowflake import ttypes
# from genpy.Snowflake import constants

CONFIG_PATH = '/scripts'

sys.path.append(CONFIG_PATH)
from db_queries import (OBJECT_QUERY_UUID_INSERT, OBJECT_QUERY_UUID_LOOKUP,
                        OBJECT_QUERY_UUID_INSERT_PARENT)
from configs import (OBJECT_FAILED_INSERTS_FILE, PROV_DB_HOST, PROV_DB_NAME,
                     PROV_DB_USERNAME, PROV_DB_PASSWORD, PROV_DB_PORT)
from prov_logging import log_errors, log_exception, log_info

# File under: things I'm thinking about on Saturday Night...
# the registration should be scoped to the service-id, right?
# consider this:
#  - Atmosphere registers an object with ``service_object_id`` of 16
#  - The DE tries to register an object with the same id, 16, and gets
#    back the UUID associated with the Atmosphere object
#
# is this "interning" of objects expected?
#
# I don't think this can be correct because the associated object_name
# and object_desc will be that of the Atmosphere request/call and not
# that of the DE call which means that when the object is looked up &
# displayed in the DE history, it'll be wrong.

def application(environ, start_response):
    """Endpoint for easy registration of provenance objects.

    It will perform the lookup, if the object does not exists, it will
    register the object return the UUID value.

    Call returns UUID if the object is found else, returns 404 NOT FOUND
    is the status code for the response.

    Keyword Arguments Defined:
    ``service_object_id`` - object identifier (used as primary key)
    ``object_name`` - name of the object
    ``object_desc`` - description of the object
    ``parent_uuid`` - the UUID of the parent object (optional)

    For more information on the arguments, see the URL definition in
    ``police_box.py``.

    Note: if the object exists, the parameters ``object_name`` and
    ``object_desc`` are ignored and the existing UUID is returned.
    """
    req = Request(environ)

    # request got routed to us, let's grab the args associated
    args, kwargs = environ['wsgiorg.routing_args']
    if (len(args) > 0):
        log_info('We should not have positional arguments: ' + args)

    if (req.method == 'POST'):
        data_string, webstatus = _handle_post(kwargs)

    else:
        data_string = json.dumps({'Status': 'Failed', 'Details':
                                 'Incorrect HTTP METHOD'}, indent=4)
        webstatus = '405 Method Not Allowed'

    response_headers = [('Content-type', 'application/json')]
    start_response(webstatus, response_headers)
    return (data_string)


def _handle_post(req_args):
    """Helper method that handles HTTP POST calls to the endpoint."""
    objid = req_args['object_id']
    objname = req_args['object_name']
    objdesc = req_args['object_desc']
    parent = req_args['parent_uuid']

    obj_data = "[" + str(objid) + "," + str(objname) + "," + \
        str(objdesc) + str(parent) + "]"

    if objid != None:
        data_string, webstatus = _register_obj(objid, objname, objdesc,
                                               obj_data, parent)

    else:
        err_msg = "Null Exception: service_object_id cannot be null " + \
            obj_data
        log_exception(err_msg)

        data_string = json.dumps(
            {'Status': 'Failed', 'Details': 'Null Exception. ' +
             'service_object_id cannot be null'}, indent=4)
        webstatus = '500 Internal Server Error'

    return data_string, webstatus


def _register_obj(obj_id, obj_name, obj_desc, obj_data, parent_uuid):
    """Handles registration of the given object information."""
    try:
        conn = MySQLdb.connect(host=PROV_DB_HOST, user=PROV_DB_USERNAME,
                               passwd=PROV_DB_PASSWORD, db=PROV_DB_NAME,
                               port=PROV_DB_PORT)
        cursor = conn.cursor()
        log_info(OBJECT_QUERY_UUID_LOOKUP % (obj_id))
        cursor.execute(OBJECT_QUERY_UUID_LOOKUP % (obj_id))
        results = cursor.fetchone()
        log_info(results)

        if results is None:
            uuid_ = get_uuid(obj_data)
            log_info(uuid_)

            if uuid_ == None:
                log_errors("Obj UUID is null: " + obj_data)
                failed_inserts_audit(obj_data)
                data_string = json.dumps({'Status': 'Failed',
                                         'Details':
                                         'Error retrieving UUID'},
                                         indent=4)
                webstatus = '503 Service Unavailable'
            else:
                data_string, webstatus = _insert_object(cursor, uuid_, obj_id,
                                                        obj_name, obj_desc,
                                                        parent_uuid)
        else:
            for value in results:
                info_msg = "Lookup: Object Exists" + " " + str(value)
                log_info(info_msg)
                data_string = json.dumps({'UUID': str(value)})
                webstatus = '200 OK'
        cursor.close()
    except Exception, e:
        err_msg = "MySQL DB Exception: " + " " + \
            str(e) + " " + obj_data
        log_exception(err_msg)
        failed_inserts_audit(obj_data)

        data_string = json.dumps({'Status': 'Failed',
                                  'Details': 'MySQL Exception. Failed' +
                                  'to retrieve data'}, indent=4)
        webstatus = '500 Internal Server Error'

    return data_string, webstatus


def _insert_object(cursor, obj_uuid, obj_id, obj_name, obj_desc, parent_uuid):
    """
    Handle the insertion of a new object.
    """
    insert = ''

    if parent_uuid is None:
        insert = OBJECT_QUERY_UUID_INSERT % (obj_uuid, obj_id, obj_name,
                                             obj_desc)
    else:
        insert = OBJECT_QUERY_UUID_INSERT_PARENT % (obj_uuid, obj_id, obj_name,
                                                    obj_desc, parent_uuid)
    log_info(insert)
    cursor.execute(insert)

    info_msg = "Object created: " + " " + str(obj_uuid)
    log_info(info_msg)
    data_string = json.dumps({'UUID': str(obj_uuid)}, indent=4)
    webstatus = '200 OK'

    return data_string, webstatus


def get_uuid(obj_data):
    """Generate and return a universal unique identifier (UUID).

    In development mode, this UUID may be generated w/ Python's ``uuid``
    module.

    In production mode, the UUID should be generated by ``Snowflake``, a
    component created by Twitter for creating robust identifiers quickly.
    """
    # generate a 128 bit integer and shift it 66 places to create an
    # 18 digit  UUID
    return int(uuid.uuid1()) >> 66

    # host = 'localhost'
    # port = 7610

    # try:
    #   socket = TSocket.TSocket(host, port)
    #   transport = TTransport.TFramedTransport(socket)
    #   protocol = TBinaryProtocol.TBinaryProtocol(transport)
    #   client = Snowflake.Client(protocol)
    #   trans_out = transport.open()

    #   timestmp = client.get_timestamp()
    #   id = client.get_id("provenanceAPI")

    #   snflake_data = "[" + str(socket) + "," + str(transport) + "," +
    #                   str(protocol) + "," + str(client) + "," + str(trans_out)
    #                   + "," + str(timestmp) + "," + str(id) + "]"
    #   info_msg = snflake_data + " " + obj_data
    #   log_info(info_msg)

    #   return id
    # except Exception, e:
    #   err_msg = "Snowflake Server exception: " + str(e) + " " + obj_data
    #   log_exception(err_msg)
    #   failed_inserts_audit(obj_data)


### why is this different? Are we just logging to a different file, so
### this is really duplicate code...
def failed_inserts_audit(data):
    """Creates an audit entry for every insertion operation that fails.

    This log is stored at ``OBJECT_FAILED_INSERTS_FILE`` and will be
    used by the ``audit_script.py`` (which is intended to run as a
    crontab)."""
    curr_time = datetime.datetime.now()
    insertfile = open(OBJECT_FAILED_INSERTS_FILE, "a")
    insertfile.write(str(curr_time) + " " + data + "\n")
    insertfile.close()
