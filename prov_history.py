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

import os
import string
import sys
import datetime
import time
import smtplib
import MySQLdb
from email.MIMEText import MIMEText
import site

CONFIG_PATH = '/scripts'

sys.path.append(CONFIG_PATH)
from db_queries import *
from configs import *
from scriptTracking import *


def insertHistory():
 
  scriptname = "History"

  try:
 
    conn = MySQLdb.connect (host = PROV_DB_HOST,user = PROV_DB_USERNAME,passwd = PROV_DB_PASSWORD,db = PROV_DB_NAME)
    cursor = conn.cursor ()
  
  except:
    
    errMsg = "Connection failed to Provenance database."
    trackHistoryExceptions(errMsg)
    notifySupport(errMsg,scriptname)
       
  try:

    cursor.execute(PARENT_HIST_SELECT_QUERY % ('Y','N'))
    p_results = cursor.fetchall()
 

    if len(p_results) != 0:
      
      for parent in p_results:

        p_id = int(parent[0])
        p_history_code = str(parent[1])
        p_uuid = int(parent[2])
        p_service_id = int(parent[3])
        p_category_id = int(parent[4])
        p_event_id = int(parent[5])
        p_username = str(parent[6])
        p_createdate = int(parent[7])

        proc_return = cursor.execute(PROV_HIST_SELECT_ID % (p_uuid,p_event_id,p_category_id,p_service_id,p_username,p_createdate))
        p_id_results = cursor.fetchall()
 

        if len(p_id_results) == 1:
          p_provenance_id = int(p_id_results[0][0])

          child_hist = cursor.execute(CHILD_HIST_SELECT_QUERY % (p_history_code,'N','N'))
          c_results = cursor.fetchall()

          for child in c_results:
            c_id = int(child[0])
            c_uuid = int(child[2])
            c_service_id = int(child[3])
	    c_category_id = int(child[4])
 	    c_event_id = int(child[5])
	    c_username = str(child[6])
	    c_createdate = int(child[7])

            c_histid_status = cursor.execute(PROV_HIST_SELECT_ID % (c_uuid,c_event_id,c_category_id,c_service_id,c_username,c_createdate))
            c_id_results = cursor.fetchall()
 
            if len(c_id_results) == 1:
               c_provenance_id = int(c_id_results[0][0])

               c_histid_status = cursor.execute(PROV_HIST_INSERT_ID % (c_provenance_id,p_provenance_id))
               if c_histid_status == 1:
                 c_process_status = cursor.execute(PROV_HIST_UPDATE_STATUS % ('Y',c_id))
                 if c_process_status == 1:
                   infoMsg = "Child row updated: " + "[parent_provenance_id,child_provenance_id]:" + "[" + str(p_id) + "," + str(c_id) + "]" 
                   trackHistoryInfo(infoMsg)
                 else:
                   errMsg = "Failed to update child row status:" + "[parent_provenance_id,child_provenance_id]:" + "[" + str(p_id) + "," + str(c_id) + "]"
                   trackHistoryErrors(errMsg)
                   notifySupport(errMsg,scriptname) 
               else:
                 errMsg = "Failed History Recording, at child rown" + "[parent_provenance_id,child_provenance_id]:" + "[" + str(p_id) + "," + str(c_id) + "]"
                 trackHistoryErrors(errMsg)
                 notifySupport(errMsg,scriptname)

            else:
               errMsg = "Error in retrieving child row from provenance table, multiple entries or no entry found. " + "[parent_provenance_id,child_provenance_id]:" + "[" + str(p_id) + "," + str(c_id) + "]"
               trackHistoryErrors(errMsg)
               notifySupport(errMsg,scriptname)

          
          p_process_status = cursor.execute(PROV_HIST_UPDATE_STATUS % ('Y',p_id))
          if p_process_status == 1:
            infoMsg = "History Recorded: " + "[parent_provenance_id]:" + "[" + str(p_id) + "]" 
            trackHistoryInfo(infoMsg)
          else:
            errMsg = "Failed updating parent row status:" + "[parent_provenance_id,child_provenance_id]:" + "[" + str(p_id) + "," + str(c_id) + "]"
            trackHistoryErrors(errMsg)
            notifySupport(errMsg,scriptname)
       
          
        elif len(p_id_results) > 1:
          errMsg = "Multiple entries found for parent row. " + "[parent_provenance_id,child_provenance_id]:" + "[" + str(p_id) + "," + str(c_id) + "]"
          trackHistoryExceptions(errMsg)
          notifySupport(errMsg,scriptname)
          
        
        else: 
          errMsg = "No entry found for parent row, but history tracking flag enabled." + "[parent_provenance_id,child_provenance_id]:" + "[" + str(p_id) + "," + str(c_id) + "]"
          trackHistoryExceptions(errMsg)
          notifySupport(errMsg,scriptname)


    cursor.close()

  except Exception, e:

    errMsg = "Exception occured after establishing DB connection: " + str(e)
    trackHistoryExceptions(errMsg)
    notifySupport(errMsg,scriptname)         
    cursor.close()

if __name__ == "__main__":
	try:
	  insertHistory()
	except:
          errMsg = "insertHistory() was not initialized"
          notifySupport(errMsg,"History") 

