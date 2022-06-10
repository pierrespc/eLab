#!/bin/python

import os
import json
import requests
import csv
import pandas
import numpy


####now preparing request
token = format(open("/Users/pierrespc/Documents/PostDocPasteur/aDNA/Import_eLAB/API_FUNCTIONALITIES/credentials/tokenELAB","r").readline().strip())
url = "https://elab-dev.pasteur.fr/api/v1/"
headers1 = {'Authorization': token, 'Accept': 'application/json','Content-Type':'application/json'}
headers2 = {'Authorization': token, 'Accept': 'application/json'}
params={}

level="Individual"
sampleTypeMetaID_toDel=244149
sampleTypeMetaID_toAdd=246288




def BadRequest(myReq,code=200):
  return(myReq.status_code !=code)
    
r = requests.get(url + "sampleTypes", headers = headers2)
if BadRequest(r,200):
    r.raise_for_status()
data = r.json()
types = {}
for typ in data.get("data"):
  types[format(typ.get("name"))] = format(typ.get("sampleTypeID"))

r = requests.get(url + "sampleTypes/" + types[level] + "/meta", headers = headers2)
if BadRequest(r,200):
  r.raise_for_status()
data = r.json()


metaInfo={}
metaBAD={}
for feat in data.get("data"):
  if feat.get("sampleTypeMetaID") == sampleTypeMetaID_toAdd:
    metaInfo["sampleDataType"]=feat.get("sampleDataType")
    metaInfo["key"]=feat.get("key")
  if feat.get("sampleTypeMetaID") == sampleTypeMetaID_toDel:
    metaBAD["sampleDataType"]=feat.get("sampleDataType")
    metaBAD["key"]=feat.get("key")
if len(metaInfo.keys())==0:
  print('not found the  meta type to add')
if len(metaBAD.keys())==0:
  print('not found the meta type to remove')

#FeateLabExe[format(feat.get("key"))] = { "ID":format(feat.get("sampleTypeMetaID")),"TYPE":format(feat.get("sampleDataType"))}





r = requests.get(url + "samples" , headers = headers2, params = {'sampleTypeID': types[level]})
if BadRequest(r,200):
    r.raise_for_status()
data = r.json()

skelEntered = {}
for sam in data.get("data"):
  #print(sam)
  ID=format(sam.get("sampleID"))
  rasID=sam.get("name")
  mr = requests.get(url + "samples/"+ID+"/meta" , headers = headers2)
  if BadRequest(mr,200):
    mr.raise_for_status()
  keep=""
  remove=""
  metaIDtoDel=None
  for fea in mr.json().get("data"):
    if fea["sampleTypeMetaID"] == sampleTypeMetaID_toDel:
      remove=fea["value"]
      metaIDtoDel=fea["sampleMetaID"]
    if fea["sampleTypeMetaID"] == sampleTypeMetaID_toAdd:
      keep=fea["value"]
  if remove != "":
    if format(remove) == "NA" or format(remove) == "nan":
      remove=""

  if remove != "":
    print(rasID+": remove->"+remove+" / and keep->"+keep)
    new=keep+remove
  else:
    new=keep
  if new == "":
    new="NA"
  metaData={"sampleTypeMetaID": sampleTypeMetaID_toAdd,
     "sampleDataType": metaInfo["sampleDataType"],
     "key": metaInfo["key"],
     "value": new}

  print(metaData)
  MDR=requests.put(url+"samples/"+format(ID)+"/meta",headers=headers2,data=metaData)
  if BadRequest(MDR,204):
      MDR.raise_for_status()

  if metaIDtoDel is not None:
    print("deleting for "+rasID)
    DELreq=requests.delete(url+"samples/"+format(ID)+"/meta/"+format(metaIDtoDel),headers=headers2)
    if BadRequest(DELreq,204):
      DELreq.raise_for_status()
  #if rasID == "AR0004":
  #  break

