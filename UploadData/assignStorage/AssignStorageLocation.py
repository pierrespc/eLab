 #!/bin/python

####Now preparing all required python libs"
import os
import json
import requests
import csv
import pandas
import numpy
from apiclient import discovery, errors
from httplib2 import Http
from oauth2client import client, file, tools
import os.path
import sys
import re

sys.path.insert(0,'../../FunctionDefinitions/')
from eLabAPIfunction import *
  
########read arguments
if len(sys.argv) != 4:
        exit("<input file>\n<delimiter (semicolon or tab in whole letter>\n<tokenID>")


CSVfilename=str(sys.argv[1])
delimiterFile=str(sys.argv[2])
tokenFile=str(sys.argv[3])

if delimiterFile == "tab":
	delimiterFile="\t"
elif delimiterFile == "semicolon":
	delimiterFile=";"
else:
	exit(delimiterFile+" not recognized")



token = format(open(tokenFile,"r").readline().strip())
url = "https://elab-dev.pasteur.fr/api/v1/"
headers1 = {'Authorization': token, 'Accept': 'application/json','Content-Type':'application/json'}
headers2 = {'Authorization': token, 'Accept': 'application/json'}






###prepare storage
storageByID={}
r=requests.get(url+"/storageLayers",headers=headers1)
stoData=r.json().get("data")
for sto in stoData:
    storageByID[sto["storageLayerID"]]={"name":sto["name"],"parentID":sto["parentStorageLayerID"]}
    #print(sto["name"])
    
storage={}
for stoID in storageByID.keys():
    name=getParentSto(stoID,storageByID)
    storage[name]=stoID
    
print(storage)

#Prepare all the eLab-API keys necessary to down and upload data

r = requests.get(url + "sampleTypes", headers = headers2)
if BadRequest(r,200):
    print("Bad request")
data = r.json()
types = {}
for typ in data.get("data"):
    types[format(typ.get("name"))] = format(typ.get("sampleTypeID"))

print(types)

r = requests.get(url + "sampleTypes/" + types["Extract"] + "/meta", headers = headers2)
if BadRequest(r,200):
    print("Bad request")
data = r.json()
FeateLabExe = {}
for feat in ['Name','Description','Note','Amount','Unit',"parentSampleID"]:
    FeateLabExe[feat] = {"ID": "notMeta"}
for feat in data.get("data"):
    FeateLabExe[format(feat.get("key"))] = { "ID":format(feat.get("sampleTypeMetaID")),
                                              "TYPE":format(feat.get("sampleDataType"))}

registered = {}
for name in types:
    ID=types[name]
    print(name + " --> " + format(ID))
    r = requests.get(url + "samples" , headers = headers2, params = {'sampleTypeID': ID})
    if BadRequest:
        r.raise_for_status()
    data = r.json()
    myList = {}
    for sam in data.get("data"):
        if format(sam.get("name")) in myList.keys():
            print(name + ": " + sam.get("name") + " duplicated")
            break
        myList[format(sam.get("name"))]=format(sam.get("sampleID"))
    registered[name] = myList
print("finished")


#Read the file with storage specifications and iterize to move sample
Table=pandas.read_csv(CSVfilename,delimiter=delimiterFile)

patternDict={"Skeleton Element":'[A][R][0-9][0-9][0-9][0-9][.][0-9]',
         "Extract":'[A][R][0-9][0-9][0-9][0-9][.][0-9][.][0-9]'}


for index,name in Table["ID"].items():
    Loc=Table.loc[index,"Location"]
    sampType="??"
    for typKey,pattern in patternDict.items():
        if re.match(pattern,name):
            sampType=typKey
    if sampType == "??":
        print(name+" has not a recognized pattern and is skipped")
    #print(sampType)
    if name not in registered[sampType]:
        print(name+" ("+typKey+") is not found in eLab and is skipped")
    if Loc not in storage.keys():
            print(name+ " has wriong location ("+Loc+") and is skipped")
    idSam=format(registered[sampType][name])
    idLoc=format(storage[Loc])
    r = requests.post(url + "samples/"+idSam+"/moveToLayer/"+idLoc, headers = headers2, params = {})
    if BadRequest(r,204):
        print(name+" "+Loc)
        r.raise_for_status()
        
print("finished")
