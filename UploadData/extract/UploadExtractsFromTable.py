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
delimiterFile=str(sys.argv[2])
tokenFile=str(sys.argv[3])
defaultPrompt=str(sys.argv[4])

if delimiterFile == "tab":
  delimiterFile="\t"
elif delimiterFile == "semicolon":
  delimiterFile=";"
else :
  exit(delimiterFile+" not recognized")


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


r = requests.get(url + "sampleTypes/" + types["Skeleton Element"] + "/meta", headers = headers2)
if BadRequest(r,200):
  r.raise_for_status()
data = r.json()
FeateLabSkel= {}
for feat in ['Name','Description','Note','Amount','Unit',"parentSampleID"]:
  FeateLabSkel[feat] = {"ID": "notMeta"}
for feat in data.get("data"):
  FeateLabSkel[format(feat.get("key"))] = { "ID":format(feat.get("sampleTypeMetaID")),"TYPE":format(feat.get("sampleDataType"))}


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
    if BadRequest(r,200):
        r.raise_for_status()
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
        if BadRequest(r,200):
            r.raise_for_status()
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
        if BadRequest(MDR,200):
            MDR.raise_for_status()
        data=MDR.json().get("data")
        metaLoaded={}
        for i in data:
            metaLoaded[i["key"]]=str(i["value"])

    for fea in FeateLabExe.keys():
        needToPatch=False
        MDR=requests.get(url + "samples/"+id+"/meta", headers = headers2)
        if BadRequest(MDR,200):
            MDR.raise_for_status()
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
                if BadRequest(MDR,204):
                    MDR.raise_for_status()
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
    if BadRequest(QR,204):
        QR.raise_for_status()

    ###put actual weight in note when there is a "<"
    if Note is not None:
            r=requests.get(url + "samples/"+id, headers = headers2)
            if BadRequest(r,200):
                r.raise_for_status()
            Data=r.json()
            Data["note"]=Data["note"]+" / "+ Note
            r=requests.patch(url + "samples/"+id, headers = headers2,data = Data)
            if BadRequest(r,204):
                r.raise_for_status()


print("Extract assignation to experiments")
print("First retrieve the eLab ID needed to access the sampleIN and sampleOUT sections.")

r = requests.get(url + "experiments", headers = headers2,params = params)
data = r.json()
experiments = {}
for exp in data.get("data"):
    experiments[format(exp.get("name"))] = format(exp.get("experimentID"))



for expe in list(experiments.keys()):
    #print(expe)
    idExpe=experiments[expe]
    r=requests.get("https://elab-dev.pasteur.fr/api/v1/experiments/"+idExpe+"/sections",headers=headers1)
    if r.status_code != 200:
        print(r.status_code)
        print(r.raise_for_status())
    if r.json().get("recordCount") == 0:
        print("no record")
        continue
    SampleIN={}
    SampleOUT={}
    for data in r.json().get("data"):
        if data["sectionType"] == "SAMPLESIN":
            SampleIN[data["sectionHeader"]]=data["expJournalID"]
        elif data["sectionType"] == "SAMPLESOUT":
            SampleOUT[data["sectionHeader"]]=data["expJournalID"]
    experiments[expe]={"ID":idExpe,
                      "sampleIN":SampleIN,
                      "sampleOUT":SampleOUT}
#print(experiments)


print("Assign to Drilling /LAB/ Laboratory Protocols,")
print("Where /LAB/ is the Lab appearing in DrillingProtocole colum")
print("pulverized pieces (sampleOUT) and  the skeleton elements they derive from (sampleIN)")
###We start retrieving all field IDs required for that
#the sampleIN and sampleOUT id for the experiment
CorresExtract={"petrous":"Pulverized petrous bone",
                  "dental calculus":"Scratched Dental Calculus",
                  "pulp":"Pulverized Pulp",
                  "root":"Pulverized Root",
                   "root apex":"Pulverized Root Apex",
                  "long bone":"Pulverized long bone",
                    "other":"Pulverized other bone",
              }
CorresSkel={"Dental Calculus":"Tooth processed",
            "Petrous":"Petrous bone processed",
            "Tooth":"Tooth processed",
            "Other Bone":"Long bone processed "}

listOUT={}
listIN={}
for lab in ["Guraeib","Del Papa","Schroeder","Rascovan","Rascovan 2.0"]:
    listOUT[lab]={}
    listIN[lab]={}
    for exType in CorresExtract:
        listOUT[lab][CorresExtract[exType]]=[]

    for skelType in CorresSkel:
        listIN[lab][CorresSkel[skelType]]=[]


for index, extract in extractTable["ExtractID"].items():
    if format(extract)=="nan":
        continue
    protocole=extractTable["DrillingProtocole"][index]
    if protocole is None:
        continue
    idOUT=registered["Extract"][extract]
    MER=requests.get(url+"/samples/"+idOUT+"/meta",headers=headers1)
    if BadRequest(MER,200):
        MER.raise_for_status()
    #get Extract Type and check it is found
    exType=None
    for meta in MER.json().get("data"):
        if meta["key"]=="Extract Type":
            exType=meta["value"]
            break
    if exType is None:
        print("Extract Type not found")
        break
    ###prepare sampleIN for that extract
    #get parentSampleID (the skeleton element)
    ER=requests.get(url+"/samples/"+idOUT,headers=headers1)
    if BadRequest(ER,200):
        ER.raise_for_status()
    idIN=format(ER.json()["parentSampleID"])

    #get meta
    SMR=requests.get(url+"/samples/"+idIN+"/meta",headers=headers1)
    if BadRequest(SMR,200):
        SMR.raise_for_status()

    ##get skeleton element type and check it is found
    archoID=None
    skelType=None
    expediente=None
    for meta in SMR.json().get("data"):
        if meta["key"]=="Bone type":
            skelType=meta["value"]
    if skelType is None:
        print("Skeleton Ele Type not found")
        print(SMR.json().get("data"))
        break

    listOUT[protocole][CorresExtract[exType]].append(idOUT)
    listIN[protocole][CorresSkel[skelType]].append(idIN)
    
#print(listIN)
#print(listOUT)
    

###upload sample IN
for lab in ["Guraeib","Del Papa","Schroeder","Rascovan","Rascovan 2.0"]:
    for type in listIN[lab].keys():
        data=listIN[lab][type]
        if len(data)==0:
            continue
            #print("sample IN : nothing to upload upload for "+type+" to "+lab)

        idIN=format(experiments["Drilling. "+lab+" Laboratory Protocols"]["sampleIN"][type])
        print("sample IN : upload for "+type+" to "+lab)
        data=format(data)
        r=requests.put(url+"/experiments/sections/"+idIN+"/samples",headers=headers1,data = data)
        if BadRequest(r,204):
            r.raise_for_status()

###upload sample OUT
for lab in ["Guraeib","Del Papa","Schroeder","Rascovan","Rascovan 2.0"]:
    for type in listOUT[lab].keys():
        data=listOUT[lab][type]
        if len(data)==0:
            #print("sample OUT : nothing to upload upload for "+type+" to "+lab)
            continue        
        idOUT=format(experiments["Drilling. "+lab+" Laboratory Protocols"]["sampleOUT"][type])
        print("sample OUT : upload for "+type+" to "+lab)
        data=format(data)
        r=requests.put(url+"/experiments/sections/"+idOUT+"/samples",headers=headers1,data = data)
        if BadRequest(r,204):
            r.raise_for_status()

print("Assign to Extraction /LAB/ Laboratory Protocols,")
print("Where /LAB/ is the Lab appearing in ExtractionProtocole colum")
print("Now we add in as sampleIN and sampleOUT the pulverized bone")

listIN={}
for lab in ["Schroeder","Rascovan","Rascovan 2.0"]:
    listIN[lab]=[]

for index, extract in extractTable["ExtractID"].items():
    if format(extract) == "nan":
        continue
    protocole=extractTable["ExtractionProtocole"][index]
    if format(protocole) == "nan":
        continue
    idIN=registered["Extract"][extract]
    listIN[protocole].append(idIN)
print(listIN)
for lab in ["Schroeder","Rascovan","Rascovan 2.0"]:
    data=format(listIN[lab])
    if format(data)=="[]":
        print("sample OUT : nothing to upload for extraction to "+lab)
    else:
        print(data)
        ###assign to sampleIN
        idExp={"c":str(value) for key, value in experiments["Extraction. "+lab+" Lab Protocols"]["sampleIN"].items()}["c"]
        r=requests.put(url+"/experiments/sections/"+idExp+"/samples",headers=headers1,data = data)
        if BadRequest(r,204):
            r.raise_for_status()
        ###assign to sampleOUT
            idExp={"c":str(value) for key, value in experiments["Extraction. "+lab+" Lab Protocols"]["sampleOUT"].items()}["c"]
        r=requests.put(url+"/experiments/sections/"+idExp+"/samples",headers=headers1,data = data)
        if BadRequest(r,204):
            r.raise_for_status()



print("Extract assignation to Storage")
print("first organize the storage IDs (a bit messy but eLab treats all storage levels similarly for sample assignation")
storageByID={}
r=requests.get(url+"/storageLayers",headers=headers1)
if BadRequest(r,200):
    r.raise_for_status()
    
stoData=r.json().get("data")
for sto in stoData:
    
    storageByID[sto["storageLayerID"]]={"name":sto["name"],"parentID":sto["parentStorageLayerID"]}

def getParentSto(ID,stoDict):
    if stoDict[ID]["parentID"]==0:
        return(stoDict[ID]["name"])
    else:
        return(getParentSto(stoDict[ID]["parentID"],stoDict)+", "+stoDict[ID]["name"])
    
storage={}
storageRev={}
for stoID in storageByID.keys():
    name=getParentSto(stoID,storageByID)
    storage[name]=stoID
    storageRev[stoID]=name

print("Now assign extracts to that storage, accordingly to the storageLayerID column.")


for index,name in extractTable[ExeDict['Name']].items():
    if format(name)=="nan":
        continue
    idEx=registered["Extract"][name]    
    freezer=extractTable["Freezer"][index]
    if format(freezer) in ["To be spotted","nan"] :
        freezer="Unknown"
    freezer=freezer.replace("Mariano Del Papa calculus to extract","Mariano Del Papa calculus extraction")
    freezer=freezer.replace("A1+A2","A1 + A2")
    freezer=freezer.replace("B1+B2","B1 + B2")
    freezer=freezer.replace("sub-bag B1+B2 ","")
    freezer=freezer.replace("sub-bag B1 + B2 ","")
    freezer=freezer.replace("sub-bag ","")
    freezer=freezer.replace("pulps","pulp")
    freezer=freezer.replace("roots","root")
    freezer=freezer.replace(" for back-up"," back-up")
    freezer=freezer.replace(" for extraction"," extraction")
    freezer=freezer.replace(" to extract"," extraction")
    freezer=freezer.replace("freezer","Freezer")
    freezer=freezer.replace("Thomas","Tom")
    freezer=freezer.replace("Hannes'","Hannes")
    freezer=freezer.replace("Hanness","Hannes")
    freezer=freezer.replace("Miren drawer","Miren Drawer 2")
    freezer=freezer.replace("blue rack","Blue Rack 1")
    freezer=freezer.replace(", front extraction clean room 159","")
    freezer=freezer.replace("Neme San Rafael","neme san rafael")
    freezer=freezer.replace(", bag mix batch,",", bag Mix batch,")
    freezer=freezer.replace("bag C group sensitive, blue box (back-up)","bag A1 + A2, C group sensitive, blue box, back-up")
    if freezer not in storage:
        print(freezer+" not registered in eLab")
        break
    r=requests.get(url+"/samples/get?sampleID="+idEx,headers=headers2)
    if BadRequest(r,200):
        r.raise_for_status()
    storedIn=r.json()[0]["storageLayerID"]
    needToMove=True
    if storedIn != 0:
        if storageRev[storedIn] != freezer:
            print(name+" already in storage: "+storageRev[storedIn])
            prompt=defaultPrompt
            while prompt not in ["y","n"]:
                prompt=input("Do you want to move it to "+ freezer+"? y/n")
                print(prompt)
            if prompt == "n":
                needToMove=False
    if needToMove:
        IDsto=format(storage[freezer])
        r=requests.post(url+"/samples/moveToLayer/"+IDsto+"?sampleIDs="+idEx,headers=headers1,data={})
        if BadRequest(r,204):
            r.raise_for_status()


print("Add description from GeneralSampleComment to Skeletal Element")
alreadyUpdated={}

for index,rasID in extractTable['RascovanLabID'].items():
    if format(rasID)=="nan":
        continue
    if rasID in alreadyUpdated.keys():
        continue
    element=extractTable.loc[index,"GeneralSampleComment"]
    r=requests.get(url + "samples/"+registered["Skeleton Element"][rasID]+"/meta", headers = headers2)
    if BadRequest(r,200):
       r.raise_for_status() 
    for fea in r.json().get("data"):
        if fea["key"] == "Observation Drilling":
            elementLoaded=fea["value"]
            if format(elementLoaded)!="nan":
                element=elementLoaded+" "+element
            MetaData={"key": "Observation Drilling",
                "sampleTypeMetaID": int(FeateLabSkel["Observation Drilling"]['ID']),
                "value": element,
                "sampleDataType": FeateLabSkel["Observation Drilling"]['TYPE']}
        
        DR=requests.put(url + "samples/"+registered["Skeleton Element"][rasID]+"/meta", headers = headers2,data = MetaData)
        if BadRequest(DR,204):
            DR.raise_for_status()
        alreadyUpdated[rasID]=element
print("finished")
    






