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
if len(sys.argv) != 5:
        exit("<input file>\n<delimiter (semicolon or tab in whole letter>\n<tokenID>\n<defaultPrompt")

#Change the default prompt line:
#put y if you are sure you want to overwrite already loaded info in eLab,
#put n if you are sure you want to leave already loaded info in eLab (although it doesn't match info in your table)
#put anything else if you want a case by case prompt

CSVfilename=str(sys.argv[1])
delimiterFileWL=str(sys.argv[2])
tokenFile=str(sys.argv[3])
defaultPrompt=str(sys.argv[4])

if delimiterFileWL == "tab":
  delimiterFile="\t"
elif delimiterFileWL == "semicolon":
  delimiterFile=";"
else :
  exit(delimiterFileML+" not recognized")


if defaultPrompt not in ['y','n','?']:
  exit(defaultPrompt+" not recognized")


####now preparing request
token = format(open(tokenFile,"r").readline().strip())
url = "https://elab-dev.pasteur.fr/api/v1/"
headers1 = {'Authorization': token, 'Accept': 'application/json','Content-Type':'application/json'}
headers2 = {'Authorization': token, 'Accept': 'application/json'}
params={}
    
#Reading the data. ExeDict is to make sure thta if eLab configuration change we justy need to change here and not the excel template. "
 
ExeDict={"Name":"ExtractID",
          "From Skeleton Element":"RascovanLabID",
          "Description":"Description",
          "Note":"Notes",
          "Amount":"Weight",
          "Unit":"fixed_gram",
          "parentSampleID":"RascovanLabID",
          "Date of drilling":"Date",
          "Pictures":"Pictures",
          "Person in charge":"PersonInCharge",
          "Laboratory where processed":"Laboratory",
          "Extract Type":"ExtractType",
          "Conservation":"Observation",
          "Pathology":"Pathologie",
          "Pathology description":"None",
          "Taken for extraction":"TakenForExtraction",
          "Extracted":"Extraction",
          "Extraction Comment":"extractionComment",
          "density UDG treatment (ng/uL)":"densityUDGtreated",
          "Volume UDG treatment (uL)":"volumeUDGtreated",
          "mass UDG in Tube (ng)":"massInTube"
    }

#extractTable=pandas.read_csv(CSVfilename,delimiter=delimiterFile,index_col=0)
extractTable=pandas.read_csv(CSVfilename,delimiter=delimiterFile)
#Prepare all the eLab-API keys necessary to down and upload data
   
def BadRequest(myReq,code=200):
  return(myReq.status_code !=code)
    
r = requests.get(url + "sampleTypes", headers = headers2)
if BadRequest(r,200):
    r.raise_for_status()
data = r.json()
types = {}
for typ in data.get("data"):
  types[format(typ.get("name"))] = format(typ.get("sampleTypeID"))
    
print(types)
    
r = requests.get(url + "sampleTypes/" + types["Extract"] + "/meta", headers = headers2)
if BadRequest(r,200):
  r.raise_for_status()
data = r.json()
FeateLabExe = {}
for feat in ['Name','Description','Note','Amount','Unit',"parentSampleID"]:
  FeateLabExe[feat] = {"ID": "notMeta"}
for feat in data.get("data"):
  FeateLabExe[format(feat.get("key"))] = { "ID":format(feat.get("sampleTypeMetaID")),"TYPE":format(feat.get("sampleDataType"))}
  

#Fill RascovanLabID or extractID columns in the table"

###get number of extracts  for skeleton elements
r = requests.get(url + "samples" , headers = headers2, params = {'sampleTypeID': types["Extract"]})
if BadRequest(r,200):
  r.raise_for_status()
data = r.json()
extractEntered = {}
for sam in data.get("data"):
    extract=format(sam.get("name"))
    rasID=".".join(extract.split(".")[0:2])
    if rasID not in extractEntered.keys():
        extractEntered[rasID]=1
    else:
        extractEntered[rasID]=extractEntered[rasID]+1

#make "From Skeleton Element column" or extract column
###change date format if needed
for index,name in extractTable["ExtractID"].items():
    ###case need to make RascovanLabID
    if format(name) != "nan" and format(extractTable.loc[index,"RascovanLabID"]) == "nan":
        extractTable.loc[index,"RascovanLabID"]=".".join(name.split(".")[0:2])
    ###case need to make extract
    elif format(name) == "nan" and format(extractTable.loc[index,"RascovanLabID"]) != "nan":
        if extractTable.loc[index,"RascovanLabID"] not in extractEntered.keys():
            numExt=1
        else:
            numExt=extractEntered[extractTable.loc[index,"RascovanLabID"]]+1
        extractEntered[extractTable.loc[index,"RascovanLabID"]]=numExt
        if numExt < 10:
            numExt="0"+str(numExt);
        else:
            numExt=str(numExt)
        extractTable.loc[index,"ExtractID"]=extractTable.loc[index,"RascovanLabID"]+"."+numExt
    elif format(name) == "nan" and format(extractTable.loc[index,"RascovanLabID"]) == "nan":
        print("must enter an extract or a skeleton id")
        print(extractTable.loc[index,])
        raise()
    else:
      print(extractTable.loc[index,])
      exit("can not enter an extract AND a skeleton id")
        
    
    if "/" in format(extractTable.loc[index,"Date"]):
        extractTable.loc[index,"Date"]="-".join(extractTable.loc[index,"Date"].split("/")[::-1])


print("Assign some columns that are fixed (e.g. drilling protocoles, person in charge).")
r = requests.get(url + "sampleTypes/" + types["Extract"] + "/meta/", headers = headers2)
if BadRequest(r,200):
    r.raise_for_status()

r=r.json().get("data")

for FixedColumn in ["Person in charge","Laboratory where processed"]:
    listPossible=""
    if len(extractTable[ ExeDict[FixedColumn]].unique()) == 1:
        for feat in r:
            if feat["key"] ==  FixedColumn:
                if feat["sampleDataType"]=="COMBO" or feat["sampleDataType"]=="CHECKBOX":
                    listPossible=feat["optionValues"]
                else:
                    listPossible="Anything"
                break
        prompt = input("put an unique value for "+FixedColumn+"\npossibilities are "+" / ".join(listPossible))
        while prompt not in listPossible and listPossible != "Anything" :
            prompt = input("put an unique value for "+FixedColumn+"\npossibilities are "+" / ".join(listPossible))
        extractTable[ExeDict[FixedColumn]]=prompt
  

extractTable["DrillingProtocole"]=input("enter an unique Drilling Protocole for that extracts?")

###Check the columns in extract Table are recognized here. If no lines in output, you are just fine.
for feat in FeateLabExe.keys():
    if feat not in ExeDict.keys():
        exit(feat + "--> NOT IN DICTIONARY")
        
for feat in ExeDict.keys():
    if feat not in FeateLabExe.keys():
        exit(feat + "--> NOT IN eLAB")


###We get all the possible values for checkboxes and dropdown features of Extracts and check our extractTable table is fine. If no lines in output, you're just fine
r = requests.get(url + "sampleTypes/" + types["Extract"] + "/meta", headers = headers2)
data = r.json()
for feat in data.get("data"):
    if feat.get("sampleDataType") == "CHECKBOX" or feat.get("sampleDataType") == "COMBO":
        OptionELAB=feat.get("optionValues")
        key=feat.get("key")
        if ExeDict[key].startswith("fixed"):
            tabVal=ExeDict[key].split("_")[1]
            if tabVal not in OptionELAB:
                exit("--" + tabVal + "-- not mapped in eLab for " + key)
        else:
            extractTable.loc[extractTable[ExeDict[key]].isnull(),ExeDict[key]]="NA"
            for tabVal in extractTable[ExeDict[key]].unique():
                if tabVal not in OptionELAB:
                    exit("--" + tabVal + "-- not mapped in eLab for " + key)

#Now, we make the json for each extract and we upload or update in eLab! 
####get all registered skeleton element and extracts
registered = {}
for name in ["Skeleton Element","Extract"]:
    print(name)
    r = requests.get(url + "samples" , headers = headers2, params = {'sampleTypeID': types[name]})
    BadRequest(r,200)
    data = r.json()
    myList = {}
    for sam in data.get("data"):
        if format(sam.get("name")) in myList.keys():
            print(name + ": " + sam.get("name") + " duplicated")
            break
        myList[format(sam.get("name"))]=format(sam.get("sampleID"))
    registered[name] = myList



###iterate over extracts in table
for index,name in extractTable[ExeDict['Name']].items():
    if format(name)=="nan":
        continue
    del(r)
    patch=False
        
    ###get what is already uploaded fior that extract in eLab
    if name in registered['Extract'].keys():
        patch=True
        id=registered['Extract'][name]
        r=requests.get(url + "samples/"+id, headers = headers2)
        BadRequest(r,200)
        r=r.json()
        
        ###change to lower case all the keys because API sometimes use upper, lower for different request (A MESS!)
        dataLoaded={}
        for oldkey in r:
            newkey=oldkey.lower()
            dataLoaded[newkey] = r[oldkey]
    ####prepare the Data to be loaded
    Data={}
    for fea in FeateLabExe.keys():
        if FeateLabExe[fea]['ID'] == "notMeta" and fea not in ["Amount","Unit"]:
            ###fixed value (from dico)
            if ExeDict[fea].startswith("fixed"):
                element=ExeDict[fea].split("_")[1]
            elif ExeDict[fea]=="None":
                element="Nothing entered"
            elif fea == "parentSampleID":
                if not name.startswith("Blank"):
                    element=registered["Skeleton Element"][extractTable["RascovanLabID"][index]]
                else:
                    element=None
            else:
                element=extractTable[ExeDict[fea]][index]

            ###check delta when patching
            if patch:
                elementLoaded=dataLoaded[fea.lower()]
                if format(elementLoaded) != format(element):
                    print("For extract "+name+", do you want to update the "+fea+" field? That is: "+format(element)+ " vs what already loaded: "+format(elementLoaded))
                    prompt=defaultPrompt
                    while prompt not in ["y","n"]:
                        prompt = input("replace y/n??")
                    print(prompt)
                    if prompt == "n":
                        element=elementLoaded
            Data[fea]=element
    ###case of updating
    if patch:
        DR=requests.patch(url + "samples/"+id, headers = headers2,data = Data)
        if BadRequest(DR,204):
            DR.raise_for_status()
    else:
        ###case of uploading
        #print(name + "uploading")
        patch=False
        Data["sampleTypeID"]=types["Extract"]
        Data["Name"]=name
        DR=requests.post(url + "samples/", headers = headers2,data = Data)   
    ####check the Data loading was correct
    if BadRequest(DR,204):
        DR.raise_for_status()
    ###actualize the registered["Site"] list (checking we did not duplicated anything here)
    r=requests.get(url + "samples/forNames?names="+name, headers = headers2)
    if BadRequest(r,200):
        r.raise_for_status()
    data=r.json()
    sam=data.get("data")
    if len(sam)!=1:
        print("different Extract entries (" + str(len(sam)) + ") for name "+name)
        break
    else:
        sam=sam[0]
        id=str(sam.get("sampleID"))
        #print("Data OK for "+ name + " (" + id + ")")
        registered["Extract"][name]=id

    ###patch the metaData
    if patch:
        #print("patching meta so need to heck if differences for "+name)
        MDR=requests.get(url + "samples/"+id+"/meta", headers = headers2)
        BadRequest(MDR,200)
        data=MDR.json().get("data")
        metaLoaded={}
        for i in data:
            metaLoaded[i["key"]]=str(i["value"])

    for fea in FeateLabExe.keys():
        needToPatch=False
        MDR=requests.get(url + "samples/"+id+"/meta", headers = headers2)
        BadRequest(MDR,200)
        ###get new element to be loaded
        if FeateLabExe[fea]['ID'] != "notMeta" and FeateLabExe[fea]['TYPE'] != "FILE":
            ###fixed value (from dico)
            if ExeDict[fea].startswith("fixed"):
                element=ExeDict[fea].split("_")[1]
                MetaData={"key": fea,
                          "sampleTypeMetaID": int(FeateLabExe[fea]['ID']),
                          "value": element,
                          "sampleDataType": FeateLabExe[fea]['TYPE']}
            elif ExeDict[fea]=="None":
                element="Nothing entered"
                MetaData={"key": fea,
                          "sampleTypeMetaID": int(FeateLabExe[fea]['ID']),
                          "value": element,
                          "sampleDataType": FeateLabExe[fea]['TYPE']}
            elif fea == "From Skeleton Element":
                if not name.startswith("Blank"):
                    sisi=extractTable["RascovanLabID"][index]
                    IDsisi=registered["Skeleton Element"][sisi]
                    element=sisi+"|"+IDsisi
                    samples={"sampleID": IDsisi,"name": sisi}
                else:
                    samples=[]
                    splitted=extractTable["extractionComment"][index].split(",")
                    splitted=list(dict.fromkeys(splitted))
                    for sisi in splitted:
                        IDsisi=registered["Extract"][sisi]
                        samples.append({"sampleID": IDsisi,"name": sisi})
                        if sisi != splitted[0]:
                            element=element+"|"+sisi+"|"+IDsisi
                        else:
                            element=sisi+"|"+IDsisi
                MetaData={
                    "sampleTypeMetaID": int(FeateLabExe[fea]['ID']),
                    "sampleDataType": FeateLabExe[fea]['TYPE'],
                    "samples": samples,
                    "key": fea,
                    "value": element
                }
            elif fea == "Pictures":
                pictures=extractTable[ExeDict[fea]][index]
                if pictures == "T":
                    element="/pasteur/entites/metapaleo/Research/ERC-project/Samples/pictures/Drilling/"+extractTable["RascovanLabID"][index]
                else:
                    element="None"
                MetaData={"key": fea,
                          "sampleTypeMetaID": int(FeateLabExe[fea]['ID']),
                          "value": element,
                          "sampleDataType": FeateLabExe[fea]['TYPE']}
            else:
                element=extractTable[ExeDict[fea]][index]
                if format(element)=="nan" or format(element)=="" or format(element)==" ":
                    element="Nothing entered"
                MetaData={"key": fea,
                          "sampleTypeMetaID": int(FeateLabExe[fea]['ID']),
                          "value": element,
                          "sampleDataType": FeateLabExe[fea]['TYPE']}
            
            ###check if this is a new entry or not
            if patch:
                ###check if new element is similar to what already loaded
                if fea not in metaLoaded.keys(): 
                    needToPatch=True
                elif metaLoaded[fea] != str(element):
                    print("difference for " + name + "(feature: " + fea + ") " + element + " vs loaded : " + metaLoaded[fea])
                    prompt=defaultPrompt
                    while prompt not in ["y","n"]:
                        prompt = input("???replace y/n??")
                    if prompt == "y":
                        needToPatch=True
            else:
                needToPatch=True
                        
            if needToPatch:
                #print(MetaData)      
                MDR=requests.put(url + "samples/"+id+"/meta", headers = headers2,data = MetaData)
                ####check the MetaData loading was correct
                BadRequest(MDR,204)
    #print("metadata OK for "+ name + " (" + id + ")")
    ###patch the quantity
    Quant={}
    Note=None
    for fea in ['Amount','Unit']:
        if ExeDict[fea].startswith("fixed"):
            element=ExeDict[fea].split("_")[1]
        elif ExeDict[fea]=="None":
            element="Nothing entered"
        else:
            element=extractTable[ExeDict[fea]][index]
            if format(element)=="nan":
                element=0
            elif "<" in format(element):
                Note="actual weight reported: "+element
                element=0
        Quant[fea]=element
    Quant["displayUnit"]=Quant["Unit"].capitalize()
    Quant["fullAmount"]=Quant["Amount"]
    QR=requests.put(url + "samples/" + id + "/quantity", headers = headers2, data = Quant)
    BadRequest(QR,204)

    ###put actual weight in note when there is a "<"
    if Note is not None:
            r=requests.get(url + "samples/"+id, headers = headers2)
            BadRequest(r,200)
            Data=r.json()
            Data["note"]=Data["note"]+" / "+ Note
            r=requests.patch(url + "samples/"+id, headers = headers2,data = Data)
            BadRequest(r,204)
print("finished") 





