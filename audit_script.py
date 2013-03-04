#!/usr/bin/python26

#  Copyright (c) 2011, The Arizona Board of Regents on behalf of
#  The University of Arizona
#
#  All rights reserved.
#
#  Developed by: iPlant Collaborative as a collaboration between
#  participants at BIO5 at The University of Arizona (the primary hosting
#  institution), Cold Spring Harbor Laboratory, The University of Texas at
#  Austin, and individual contributors. Find out more at
#  http://www.iplantcollaborative.org/.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * Neither the name of the iPlant Collaborative, BIO5, The University
#   of Arizona, Cold Spring Harbor Laboratory, The University of Texas at
#   Austin, nor the names of other contributors may be used to endorse or
#   promote products derived from this software without specific prior
#   written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
# Author: Sangeeta Kuchimanchi (sangeeta@iplantcollaborative.org)
# Date: 10/11/2012
#

#import os
#import string
import sys
#import fileinput
#import datetime
#import time
#import smtplib
import MySQLdb
#from email.MIMEText import MIMEText
#import site

CONFIG_PATH = '/scripts'
sys.path.append(CONFIG_PATH)

# explictly state what is used from TARDIS codebase, no ``import *``
from db_queries import (AUDIT_SELECT, AUDIT_UPDATE_STATUS, QUERY_ALL,
                        QUERY_DATA, QUERY_NO_PROXY_DATA, QUERY_PROXY)
from configs import (PROV_DB_HOST, PROV_DB_NAME, PROV_DB_USERNAME,
                    PROV_DB_PASSWORD)
from prov_logging import (log_errors, log_exception, log_info)
from script_tracking import (failed_inserts_audit, notify_support,
                            track_history_exceptions)

# consider adding context to insert and update "status codes"
#AUDIT_SUCCESS = 1

def insert_audit():
    """<add a docstring when method is fully understood>"""
    scriptname = "Audit"

    try:
        conn = MySQLdb.connect(host=PROV_DB_HOST, user=PROV_DB_USERNAME,
                               passwd=PROV_DB_PASSWORD, db=PROV_DB_NAME)
        cursor = conn.cursor()
    except:
        err_msg = "Audit: Connection failed to Provenance database."
        track_history_exceptions(err_msg)
        notify_support(err_msg, scriptname)


    try:
        cursor.execute(AUDIT_SELECT % ('N'))
        results = cursor.fetchall()

        # inconsistent indent characters makes this even _harder_ to follow
        # THOU SHALL NOT HAVE 180+ line methods with nesting this DEEP!
        if len(results) != 0:

            for row in results:
                # Python has a built-in `id`, so use _id to avoid redefining.
                _id = int(row[0])
                uuid = int(row[1])
                service_id = int(row[2])
                category_id = int(row[3])
                event_id = int(row[4])
                username = str(row[5])
                proxy_username = str(row[6])
                event_data = str(row[7])
                request_ipaddress = str(row[8])
                created_date = int(row[9])

                all_data = "{Audit row : " + str(_id) + "}"
                # no proxy_username AND no event_data
                if proxy_username is None and event_data is None:
                    insert_status = cursor.execute(QUERY_NO_PROXY_DATA %
                                                (uuid, event_id, category_id,
                                                service_id, username,
                                                request_ipaddress,
                                                created_date))
                    if insert_status == 1:
                        update_status = cursor.execute(AUDIT_UPDATE_STATUS %
                                                        ('Y', _id))
                        if update_status == 1:
                            info_msg = "Audit Success: " + all_data
                            log_info(info_msg)
                        else:
                            err_msg = ("Audit Update: AUDIT_UPDATE_STATUS " +
                                        "query failed" + all_data)
                            log_errors(err_msg)
                            failed_inserts_audit(all_data)
                            notify_support(err_msg, scriptname)
                    else:
                        err_msg = ("Audit: QUERY_NO_PROXY_DATA query failed" +
                                    all_data)
                        log_errors(err_msg)
                        failed_inserts_audit(all_data)
                        notify_support(err_msg, scriptname)
                # no proxy_username case (inside the 'if len > 0')
                elif proxy_username != None:
                    insert_status = cursor.execute(QUERY_PROXY %
                                            (uuid, event_id, category_id,
                                            service_id, username,
                                            proxy_username, request_ipaddress,
                                            created_date))
                    if insert_status == 1:
                        update_status = cursor.execute(AUDIT_UPDATE_STATUS %
                                                        ('Y', _id))
                        if update_status == 1:
                            info_msg = "Audit Success: " + all_data
                            log_info(info_msg)
                        else:
                            err_msg = ("Audit Update: AUDIT_UPDATE_STATUS " +
                                        " query failed" + all_data)
                            log_errors(err_msg)
                            failed_inserts_audit(all_data)
                            notify_support(err_msg, scriptname)
                    else:
                        err_msg = "Audit: QUERY_PROXY query failed" + all_data
                        log_errors(err_msg)
                        failed_inserts_audit(all_data)
                        notify_support(err_msg, scriptname)
                # no event_data case (inside the 'if len > 0')
                elif event_data != None:
                    insert_status = cursor.execute(QUERY_DATA %
                                                (uuid, event_id, category_id,
                                                service_id, username,
                                                event_data, request_ipaddress,
                                                created_date))

                    if insert_status == 1:
                        update_status = cursor.execute(AUDIT_UPDATE_STATUS %
                                                        ('Y', _id))
                        if update_status == 1:
                            info_msg = "Audit Success: " + all_data
                            log_info(info_msg)
                        else:
                            err_msg = ("Audit Update: AUDIT_UPDATE_STATUS " +
                                        "query failed" + all_data)
                            log_errors(err_msg)
                            failed_inserts_audit(all_data)
                            notify_support(err_msg, scriptname)

                    else:
                        err_msg = "Audit: QUERY_DATA query failed" + all_data
                        log_errors(err_msg)
                        failed_inserts_audit(all_data)
                        notify_support(err_msg, scriptname)
                else:
                # final else block
                    insert_status = cursor.execute(QUERY_ALL %
                                                (uuid, event_id, category_id,
                                                service_id, username,
                                                proxy_username, event_data,
                                                request_ipaddress,
                                                created_date))
                    if insert_status == 1:
                        update_status = cursor.execute(AUDIT_UPDATE_STATUS %
                                                        ('Y', _id))
                        if update_status == 1:
                            info_msg = "Audit Success: " + all_data
                            log_info(info_msg)
                        else:
                            err_msg = ("Audit Update: AUDIT_UPDATE_STATUS " +
                                        "query failed" + all_data)
                            log_errors(err_msg)
                            failed_inserts_audit(all_data)
                            notify_support(err_msg, scriptname)
                    else:
                        err_msg = "Audit: QUERY_ALL query failed" + all_data
                        log_errors(err_msg)
                        failed_inserts_audit(all_data)
                        notify_support(err_msg, scriptname)

        # outside the if block ...
        cursor.close()

    except Exception, e:

        err_msg = "AUDIT EXCEPTION: " + str(e) + ": " + all_data
        log_exception(err_msg)
        failed_inserts_audit(all_data)
        notify_support(err_msg, scriptname)
        cursor.close()

def main():
    """Script entry point.

    This runs an audit check and inserts any necessary audit records.
    """
    try:
        insert_audit()
    except Exception, e:
        err_msg = "insert_audit() was not initialized " + str(e)
        notify_support(err_msg, "Audit")

if __name__ == "__main__":
    main()
