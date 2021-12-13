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



def BadRequest(myReq,code=200):
  return(myReq.status_code !=code)
    
r = requests.get(url + "sampleTypes", headers = headers2)
if BadRequest(r,200):
    r.raise_for_status()
data = r.json()
types = {}
for typ in data.get("data"):
  types[format(typ.get("name"))] = format(typ.get("sampleTypeID"))




r = requests.get(url + "sampleTypes/" + types["Skeleton Element"] + "/meta", headers = headers2)
if BadRequest(r,200):
  r.raise_for_status()
data = r.json()
FeateLabSkel= {}
for feat in ['Name','Description','Note','Amount','Unit',"parentSampleID"]:
  FeateLabSkel[feat] = {"ID": "notMeta"}
for feat in data.get("data"):
  FeateLabSkel[format(feat.get("key"))] = { "ID":format(feat.get("sampleTypeMetaID")),"TYPE":format(feat.get("sampleDataType"))}



r = requests.get(url + "samples" , headers = headers2, params = {'sampleTypeID': types["Skeleton Element"]})
if BadRequest(r,200):
    r.raise_for_status()
data = r.json()

skelEntered = {}
for sam in data.get("data"):
    #print(sam)
    ID=format(sam.get("sampleID"))
    rasID=sam.get("name")
    r = requests.get(url + "samples/"+ID , headers = headers2)
    if BadRequest(r,200):
        r.raise_for_status()
    mr = requests.get(url + "samples/"+ID+"/meta" , headers = headers2)
    if BadRequest(mr,200):
       mr.raise_for_status()
    des=r.json()["description"]
    if "Comment from Drilling Session:" in des:
        print(rasID)
        comment=des.split("| Comment from Drilling Session: ")[1]
        des=des.split("| Comment from Drilling Session: ")[0]
        Pr=requests.patch(url+"samples/"+ID,headers=headers2,data = {"description":des})
        if BadRequest(Pr,204):
            Pr.raise_for_status()

        for fea in mr.json().get("data"):
            if fea["key"] == "Observation Drilling":
                MetaData={"key": "Observation Drilling",
                    "sampleTypeMetaID": int(FeateLabSkel["Observation Drilling"]['ID']),
                    "value": comment,
                    "sampleDataType": FeateLabSkel["Observation Drilling"]['TYPE']}
        
                DR=requests.put(url + "samples/"+ID+"/meta", headers = headers2,data = MetaData)
                if BadRequest(DR,204):
                    DR.raise_for_status()
    

