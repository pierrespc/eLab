 #!/bin/python

####Now preparing all required python libs"
import pandas as pd
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
from datetime import datetime

sys.path.insert(0,'../../FunctionDefinitions/')
from eLabAPIfunction import *


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

r = requests.get(url + "sampleTypes", headers = headers2)
dictType = r.json().get("data")

##Now we get all registered ID for all types. (I am lazy now to try to find a clever way to process only the types we need downstream)
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
print("finished")


print("Getting which info will be saved in the output table:")
print("We get the sample types for which we will output the info and the features we want to retrieve for each sample Type")
types = {}
for typ in dictType:
    prompt="?"
    while prompt not in ["y","n"]:
        prompt=input("interested in getting info from "+typ.get("name")+"? y/n")
    if prompt == "y":
        typName=format(typ.get("name"))
        types[typName] = {"key":format(typ.get("sampleTypeID")),
                                          "meta":{},
                                          "data":{}}
        r = requests.get(url + "sampleTypes/" + types[typName]["key"] + "/meta", headers = headers2)
        if BadRequest(r,200):
            r.raise_for_status()
        data = r.json()
        for feat in data.get("data"):
            if feat.get("sampleDataType") == "SAMPLELINK":
                continue
            prompt="?"
            while prompt not in ["y","n"]:
                prompt=input("\tinterested in outputing META feature "+feat.get("key")+"? y/n")
            if prompt == "y":
                types[typName]["meta"][feat.get("key")]=feat.get("sampleTypeMetaID")
        for feat in ["description","Quantity","note"]:
            prompt="?"
            while prompt not in ["y","n"]:
                prompt=input("\tinterested in outputing notMETA feature "+feat+"? y/n")
            if prompt == "y":
                types[typName]["data"][feat]=""
print(types)


print("NOW Defining the filters")
print("On which field and Sample type you want to filter?")
listFilter={}
levelSeq=['Library pool', 'Indexed Library', 'Non Indexed Library', 'Extract','Skeleton Element', 'Individual', 'Site']
for typ in dictType:
    typName=typ.get("name")
    if typName == "Bone pellet":
        continue
    typID=typ.get("sampleTypeID")
    level=levelSeq.index(typName)
    print(typName+" " +format(level))
    typeFilter="?"
    while typeFilter not in ["y","n"]:
        typeFilter=input("Do you want to apply a filter for "+typName+"?")
    if typeFilter == "y":
        listFilter[typName]={}
        r = requests.get(url + "sampleTypes/" + format(typID) + "/meta", headers = headers2)
        if BadRequest(r,200):
            r.raise_for_status()
        data = r.json()
        for meta in data.get("data"):
            typeFilter="?"
            while typeFilter not in ["y","n"]:
                typeFilter=input("\tfor "+ typName+", is there a filter for "+meta.get("key")+"?")
                if typeFilter == "y":
                    listFilter[typName][meta.get("key")]={}
                    r = requests.get(url + "sampleTypes/" + format(typID) + "/meta/"+format(meta.get("sampleTypeMetaID")), headers = headers2)
                    if BadRequest(r,200):
                        r.raise_for_status()
                        
                    listFilter[typName][meta.get("key")]["type"]=r.json().get("sampleDataType")

                    if r.json().get("sampleDataType") == "DATE":
                        listFilter[typName][meta.get("key")]["filter"]=getDateFilter()                           
                    elif r.json().get("sampleDataType") == "CHECKBOX":
                        listFilter[typName][meta.get("key")]["filter"]=getOptionFilter(r.json().get("optionValues"))
                    elif r.json().get("sampleDataType") == "COMBO":
                        listFilter[typName][meta.get("key")]["filter"]=getOptionFilter(r.json().get("optionValues"))
                    elif r.json().get("sampleDataType") == "TEXT":
                        listFilter[typName][meta.get("key")]["filter"]=getTextFilter()
                    elif r.json().get("sampleDataType") == "SAMPLELINK":
                        parentType=levelSeq[level+1]
                        listFilter[typName][meta.get("key")]["filter"]=getLinkFilter(typName,registered[parentType],True)
                    else:
                        print(r.json().get("sampleDataType")+" not covered")
                        break
        
        for feat in ["description","Quantity","note","name"]:
            typeFilter="?"
            while typeFilter not in ["y","n"]:
                typeFilter=input("\tfor "+ typName+", is there a filter for "+feat+"?")
            if typeFilter == "y":
                listFilter[typName][feat]={}
                if feat in ["Observation","Note"]:
                    listFilter[typName][feat]["type"]="TEXT"
                    listFilter[typName][feat]["filter"]=getTextFilter()
                elif feat == "Quantity":
                    listFilter[typName][feat]["type"]="QUANTITY"
                    listFilter[typName][feat]["filter"]=getQuantityFilter()
                else:
                    listFilter[typName][feat]["type"]="NAME"
                    listFilter[typName][feat]["filter"]=getLinkFilter(typName,registered[typName],False)
        if len(listFilter[typName])==0:
            print("you finally decided not to filter for anything for "+typName)
            del(listFilter[typName])

print("Parsing the database, filter the entry and output ")
startRecord=False
filteredEntries={}

levelNum=0
listNextStepKept="FIRSTlevelParsed"
## first we get all entries that match filter for each type
for level in levelSeq:
    levelNum=levelNum+1
    ###check if needed to record entries for that level
    if level not in listFilter.keys() and level not in types.keys() and not startRecord:
        print(level+" skipped")
        continue
    else:
        startRecord=True
        filteredEntries[level]={level:[]}
        if level!=levelSeq[len(levelSeq)-1]:          
            filteredEntries[level][levelSeq[levelNum]]=[]
            #filteredEntries[level]["parent"]=[]
        if level in types.keys():
            for entry in types[level]["meta"]:
                filteredEntries[level][level+"_"+entry]=[]
            for entry in types[level]["data"]:
                filteredEntries[level][level+"_"+entry]=[]
        print("parsing "+ level)
        #for sample,idSam in prout.items():
        for sample,idSam in registered[level].items():
            if listNextStepKept=="FIRSTlevelParsed":
                filterIN=True
            else:
                filterIN=filterName(sample,
                                    listNextStepKept,
                                    "in")
            if not filterIN:
                continue
            ##if no filter for that we keep the entry by default
            if level in listFilter.keys():
                r=requests.get(url+"/samples/get?sampleID="+idSam,headers=headers2)
                if BadRequest(r,200):
                    r.raise_for_status()
                ###filtering for observation and note (not meta data)
                if "name" in listFilter[level].keys():
                    new=filterName(sample,
                                   listFilter[level]["name"]["filter"]["list"],
                                   listFilter[level]["name"]["filter"]["rule"])
                    filterIN=filterIN and new
                if "description" in listFilter[level].keys() or "note" in listFilter[level].keys():
                    for filterTy in ["description","note"]:
                        if filterTy in listFilter[level].keys():
                            print(filterTy+" "+format(new))
                            new=filterText(r.json.get(filterTy),listFilter[level][filterTy]["filter"])
                            filterIN=filterIN and new
                if not filterIN:
                    continue


                ###filtering for quantity (not meta data)
                if "Quantity" in listFilter[level].keys():
                    r=requests.get(url + "samples/" + idSam + "/quantity", headers = headers2)
                    if BadRequest(r,200):
                        r.raise_for_status()
                    new=filterQuantity(r.json().get("amount"),
                                   listFilter[level]["Quantity"]["filter"]["quantity"],
                                   listFilter[level]["Quantity"]["filter"]["rule"])
                    #print("Quantity "+format(new))
                    filterIN=filterIN and new
                if not filterIN:
                    continue

                ###filtering for meta data fields
                r=requests.get(url+"/samples/"+idSam+"/meta",headers=headers2)
                if r.status_code != 200:
                    r.raise_for_status()
                for meta in r.json().get("data"):
                    if meta.get("key") in listFilter[level].keys():
                        if listFilter[level][meta.get("key")]["type"] == "DATE":
                            new=filterDate(meta.get("value"),listFilter[level][meta.get("key")]["filter"])
                        elif listFilter[level][meta.get("key")]["type"] == "TEXT":
                            new=filterText(meta.get("value"),listFilter[level][meta.get("key")]["filter"])
                        elif listFilter[level][meta.get("key")]["type"] == "SAMPLELINK":
                            new=filterLink(meta.get("value"),
                                           listFilter[level][meta.get("key")]["filter"]["list"],
                                           listFilter[level][meta.get("key")]["filter"]["rule"])
                        elif listFilter[level][meta.get("key")]["type"] == "COMBO":
                            new=filterCombo(meta.get("value"),listFilter[level][meta.get("key")]["filter"])
                        elif listFilter[level][meta.get("key")]["type"] == "CHECKBOX":
                            new=filterCheckbox(meta.get("value"),listFilter[level][meta.get("key")]["filter"])
                        else:
                            raise(listFilter[level][meta.get("key")]["type"]+" not covered")
                        #print(meta.get("key")+" "+format(new)+" "+format(meta.get("value")))                        
                        filterIN=filterIN and new
                if not filterIN:
                    continue

            ###if that entry passed the filter we record the required fields (and the parent sample)

            #print(sample+"-->IN")
            ##adding the name by default
            filteredEntries[level][level].append(sample)
            
            r=requests.get(url+"/samples/"+idSam+"/meta",headers=headers2)
            if r.status_code != 200:
                r.raise_for_status()
                
            ###now adding metadata and data requested by user
            for meta in r.json().get("data"):
                ##adding the the parent by default
                if meta.get("sampleDataType")=="SAMPLELINK":
                    ###that if is for a stupid stuff in elab I can't not resolve for AR0188.1
                    if level == "Skeleton Element" and meta.get("key")=="From Skeleton Element":
                        print(meta.get("key")+" skipped for "+sample)
                        continue
                    filteredEntries[level][levelSeq[levelNum]].append(meta.get("value").split("|")[0])
                    #filteredEntries[level]["parent"].append(meta.get("value").split("|")[0])
            if level in types.keys():
                found=[]
                for meta in r.json().get("data"):
                    ##adding the meta field that the user specified
                    if meta.get("key") in types[level]["meta"]:
                        filteredEntries[level][level+"_"+meta.get("key")].append(meta.get("value"))
                        found.append(meta.get("key"))
                for meta in types[level]["meta"].keys():
                    if meta not in found:
                        print("pb "+sample+" "+meta+" not found")
                        filteredEntries[level][level+"_"+meta].append("NOTineLab")
                ##adding the data field that the user specified
                if "description" in types[level]["data"] or "note" in types[level]["data"]:
                    r=requests.get(url+"/samples/"+idSam,headers=headers2)
                    if r.status_code != 200:
                        r.raise_for_status()
                    for dataTy in ["description","note"]:
                        if dataTy in types[level]["data"]:
                            filteredEntries[level][level+"_"+dataTy].append(r.json().get(dataTy))
                if "Quantity" in types[level]["data"]:
                    r=requests.get(url+"/samples/"+idSam+"/quantity",headers=headers2)
                    if r.status_code != 200:
                        r.raise_for_status()
                    filteredEntries[level][level+"_Quantity"].append(format(r.json().get("amount"))+r.json().get("unit"))
        print("we have "+format(len(filteredEntries[level][level]))+" remaining")
        # we register the parent samples from that list
        
        
        if level != "Site":
            listNextStepKept=filteredEntries[level][levelSeq[levelNum]]
        for fea in filteredEntries[level].keys():
            print(fea+": "+format(len(filteredEntries[level][fea])))
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
        out=filteredEntries[level]["df"].merge(out,how='inner',on=level)
        
out.drop_duplicates()        
## And we can write!
##first some comments to register the filters:
jiter=0
for level in listFilter.keys():
    jiter=jiter+1
    f.writelines("#"+format(jiter)+". filters at: "+level+"\n")
    iter=0
    for fifi in listFilter[level].keys():
        iter=iter+1
        f.writelines("#    -"+format(jiter)+"."+format(iter)+". "+fifi+":"+format(listFilter[level][fifi]["filter"])+"\n")
f.close()
out.to_csv(filename, sep='\t', na_rep='NA',mode='a')
        
print("DONE")



