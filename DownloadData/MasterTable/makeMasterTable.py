#!.bin/python

import sys
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
from datetime import date


########read arguments
if len(sys.argv) != 4:
	exit("<output folder> <tokenID> <selectFeatPerSample y/n>")


outFolder=str(sys.argv[1])
tokenFile=str(sys.argv[2])
selectFeat=str(sys.argv[3])

if selectFeat == "y":
	defaultPromptFeat="?"
elif selectFeat == "n": 
	defaultPromptFeat="y"
else:
	exit("<output folder> <tokenID> <selectFeatPerSample y/n>")


today = date.today().strftime("%Y-%m-%d")


filename=outFolder+"/"+today+".Master.eLab.Table.tsv"
print("will output on "+filename)

f = open(filename, 'w')
f.close()
###########functions to check requests
def BadRequest(myReq,code=200):
    return(myReq.status_code !=code)



###########function  to check filter by name
def filterName(value,listNAM,ruler):
    if ruler=="in":
        return(value in listNAM)
    elif ruler=="notin":
        return(value not in listNAM)
    else:
        raise()
 ###function to replace an empty value read in elab by "nan"
def putNan(jsonRead,key):
    if jsonRead.get(key) is not None:
        return(format(jsonRead.get(key)).replace("\n","| "))
    else:
        return("nan")

###Prepare all the eLab-API keys necessary to down and upload data. Get list of sample types user is interested in.
token = format(open(tokenFile,"r").readline().strip())
url = "https://elab-dev.pasteur.fr/api/v1/"
headers1 = {'Authorization': token, 'Accept': 'application/json','Content-Type':'application/json'}
headers2 = {'Authorization': token, 'Accept': 'application/json'}


levelSeq=['Library pool', 'Indexed Library', 'Non Indexed Library', 'Extract','Skeleton Element', 'Individual', 'Site']

r = requests.get(url + "sampleTypes", headers = headers2)
if BadRequest(r,200):
    r.raise_for_status()

tmp = r.json().get("data")
dictType=[]
for level in levelSeq:
	for typ in tmp:
		if format(typ.get("name")) == level:
			dictType.append(typ)


#Now we get all registered ID for all types.
#(I am lazy now to try to find a clever way to process only the types we need downstream)
registered = {}
for it in dictType:
    name = it.get("name")
    ID = it.get("sampleTypeID")
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


#####now we get the storage...a bit messy but diofficult to retireve the layers organiztion
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

storageByID={}
for stoID in storage.keys():
	storageByID[storage[stoID]]=stoID


print("Now we get the sample types for which we will output the info and the features we want to retrieve for each sample Type")




types = {}
for typ in dictType:
	prompt="?"
	
	while prompt not in ["y","n"]:
		prompt=input("interested in getting info from "+typ.get("name")+"? y/n")
		if prompt == "y":
			typName=format(typ.get("name"))
			types[typName] = {"key":format(typ.get("sampleTypeID")),"meta":{},"data":{}}
			r = requests.get(url + "sampleTypes/" + types[typName]["key"] + "/meta", headers = headers2)
			if BadRequest(r,200):
				r.raise_for_status()
			data = r.json()
			for feat in data.get("data"):
				if feat.get("sampleDataType") == "SAMPLELINK":
					continue
				#elif feat.get("key") == "Pictures" or feat.get("key") == "Scanned":
				#	print(feat.get("key")+" will not be outputed")
				#	continue
				prompt=defaultPromptFeat
				while prompt not in ["y","n"]:
					prompt=input("interested in outputing META feature "+feat.get("key")+"? y/n")
				if prompt == "y":
					types[typName]["meta"][feat.get("key")]=feat.get("sampleTypeMetaID")
			for feat in ["description","Quantity","note"]:
				prompt=defaultPromptFeat
				while prompt not in ["y","n"]:
					prompt=input("interested in outputing notMETA feature "+feat+"? y/n")
				if prompt == "y":
					types[typName]["data"][feat]=""



print("now retrieving the samples")
import pandas as pd

startRecord=False
filteredEntries={}

levelNum=0
listNextStepKept="FIRSTlevelParsed"
## first we get all entries that match filter for each type

for level in levelSeq:
    levelNum=levelNum+1
    ###check if needed to record entries for that level
    if level not in types.keys() and not startRecord:
        print(level+" skipped")
        continue
    else:
        startRecord=True
        filteredEntries[level]={level:[]}
        if level!=levelSeq[len(levelSeq)-1]:          
            filteredEntries[level][levelSeq[levelNum]]=[]

        if level not in ['Site','Individual']:
        	filteredEntries[level][level+"_Storage"]=[]
            #filteredEntries[level]["parent"]=[]
        
        if level in types.keys():
            for entry in types[level]["meta"]:
                filteredEntries[level][level+"_"+entry]=[]
            for entry in types[level]["data"]:
                filteredEntries[level][level+"_"+entry]=[]
        print("parsing "+ level)
        #for sample,idSam in prout.items():
        for sample,idSam in registered[level].items():
        
            filteredEntries[level][level].append(sample)
            r=requests.get(url+"/samples/"+idSam+"/meta",headers=headers2)
            if r.status_code != 200:
                r.raise_for_status()
        
            ###now adding metadata and data requested by user
            for meta in r.json().get("data"):
                ##adding the the parent by default
                if meta.get("sampleDataType")=="SAMPLELINK":
                    filteredEntries[level][levelSeq[levelNum]].append(putNan(meta,"value").split("|")[0])
                    #filteredEntries[level]["parent"].append(meta.get("value").split("|")[0])
            if level in types.keys():
                foundMeta=[]
                for meta in r.json().get("data"):
                    ##adding the meta field that the user specified
                    if meta.get("key") in types[level]["meta"]:
                        filteredEntries[level][level+"_"+meta.get("key")].append(putNan(meta,"value"))
                        foundMeta.append(meta.get("key"))
                for notfound in list(set(types[level]["meta"]) - set(foundMeta)):
                    filteredEntries[level][level+"_"+notfound].append("nan")

                    #if meta.get("key") == "Pictures":
                    #	print("Pictures:"+meta.get("value")+"-->"+putNan(meta,"value")+"??"+format(len(filteredEntries[level][level+"_"+meta.get("key")])))
                ##adding the data field that the user specified

                r=requests.get(url+"/samples/"+idSam,headers=headers2)
                if r.status_code != 200:
                	r.raise_for_status()
                if level not in ['Site','Individual']:
                	idSto=format(r.json().get("storageLayerID"))
                	if idSto == "0":
                		filteredEntries[level][level+"_Storage"].append("nan")
                	else:
                		filteredEntries[level][level+"_Storage"].append(storageByID[r.json().get("storageLayerID")])
                for dataTy in ["description","note"]:
                	if dataTy in types[level]["data"]:
                		filteredEntries[level][level+"_"+dataTy].append(putNan(r.json(),dataTy))
                if "Quantity" in types[level]["data"]:
                	r=requests.get(url+"/samples/"+idSam+"/quantity",headers=headers2)
                	if r.status_code != 200:
                		r.raise_for_status()
                	filteredEntries[level][level+"_Quantity"].append(putNan(r.json(),"amount")+putNan(r.json(),"unit"))
        print("we have "+format(len(filteredEntries[level][level]))+" remaining")


        # we register the parent samples from that list
        if level != "Site":
            listNextStepKept=filteredEntries[level][levelSeq[levelNum]]

        #for colName in filteredEntries[level].keys():
        #	print(colName+" "+format(len(filteredEntries[level][colName])))	
        filteredEntries[level]["df"]=pd.DataFrame(filteredEntries[level])




print("Now we merge the different data frames obtained for each level into an unique table!")
Starting=True
for level in levelSeq:
    if level not in types.keys() and Starting:
        print(level+" skipped")
        continue
    if Starting:
        out=filteredEntries[level]["df"]
        Starting=False
    else:
        out=filteredEntries[level]["df"].merge(out,how='outer',on=level)
        
out.drop_duplicates()        
out.to_csv(filename, sep='\t', na_rep='NA',mode='w')
        

os.system("rsync -azvh --progress -e 'ssh' "+filename+" pluisi@sftpcampus.pasteur.fr:/pasteur/entites/metapaleo/Research/ERC-project/Samples/MetaTable_fromELAB/")

