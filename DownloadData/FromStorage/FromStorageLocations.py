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

########read arguments
if len(sys.argv) != 3:
        exit("<outfile>\n<tokenID>")

filename=str(sys.argv[1])
tokenFile=str(sys.argv[2])


f = open(filename, 'w')

token = format(open(tokenFile,"r").readline().strip())
url = "https://elab-dev.pasteur.fr/api/v1/"
headers1 = {'Authorization': token, 'Accept': 'application/json','Content-Type':'application/json'}
headers2 = {'Authorization': token, 'Accept': 'application/json'}


#Prepare all the eLab-API keys necessary to down and upload data. Get list of sample types user is interested in.
def BadRequest(myReq,code=200):
    return(myReq.status_code !=code)

storageByID={}
r=requests.get(url+"/storageLayers",headers=headers1)
stoData=r.json().get("data")
for sto in stoData:
    storageByID[sto["storageLayerID"]]={"name":sto["name"],"parentID":sto["parentStorageLayerID"]}
    #print(sto["name"])
def getParentSto(ID,stoDict):
    if stoDict[ID]["parentID"]==0:
        return(stoDict[ID]["name"])
    else:
        return(getParentSto(stoDict[ID]["parentID"],stoDict)+", "+stoDict[ID]["name"])
    
    
storage={}
for stoID in storageByID.keys():
    name=getParentSto(stoID,storageByID)
    storage[name]=stoID
    



iter=-1
prev="bliblablou"

print("get the storage where to look for samples:")
listID=[]
for sto in storageByID:
    if storageByID[sto]["parentID"] == 0:
        iter=iter+1
        listID.append(storageByID[sto]["name"])        
        print(format(iter)+": "+storageByID[sto]["name"])
print(listID)
StorageToReach={}
listChoice=input("what are your choice? (the number separated by <space>)").split()
print("now we will choice the location layers within the storage")
for i in listChoice:
    idSto=listID[int(i)]
    ###we will go from the lower layers to the upper...
    upperLevel=True
    for sto in storage:
        stoSplit=sto.split(", ")
        if stoSplit[0] == idSto and len(stoSplit)>1:
            prompt="?"
            while prompt not in ["y","n"]:
                prompt=input("select layer "+ sto+" ?( y/n)")
            if prompt == "y":
                upperLevel=False
                StorageToReach[sto]={"id":storage[sto]}
    if upperLevel:
        StorageToReach[idSto]={"id":storage[idSto]}
        
            
print(StorageToReach)
            
        
import pandas as pd
out={"Sample":[],"Storage":[],"Type":[]}
for idSto in StorageToReach:
    r=requests.get(url+"/storageLayers/"+format(StorageToReach[idSto]["id"])+"/samples",headers=headers1)
    for sam in r.json().get("data"):
        out["Sample"].append(sam["name"])
        out["Storage"].append(idSto)
        out["Type"].append(sam["sampleType"]["name"])

out=pd.DataFrame(out)   
out.to_csv(filename, sep='\t', na_rep='NA',mode='w')




