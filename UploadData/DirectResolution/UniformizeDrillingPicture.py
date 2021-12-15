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




###########functions to check requests
def BadRequest(myReq,code=200):
    return(myReq.status_code !=code)

token = format(open("/Users/pierrespc/Documents/PostDocPasteur/aDNA/Import_eLAB/API_FUNCTIONALITIES/credentials/tokenELAB","r").readline().strip())
url = "https://elab-dev.pasteur.fr/api/v1/"
headers1 = {'Authorization': token, 'Accept': 'application/json','Content-Type':'application/json'}
headers2 = {'Authorization': token, 'Accept': 'application/json'}


levelSeq=[ 'Extract','Skeleton Element']


r = requests.get(url + "sampleTypes", headers = headers2)
if BadRequest(r,200):
	r.raise_for_status()
data = r.json()
types = {}
for typ in data.get("data"):
	types[format(typ.get("name"))] = format(typ.get("sampleTypeID"))



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






#Now we get all registered ID for all types.
#(I am lazy now to try to find a clever way to process only the types we need downstream)
registered = {}
for name in types:
	
	ID = types[name]
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



for extractName in registered["Extract"].keys():
#for extractName in ["AR0138.1.01"]:
	if extractName.startswith("Blank"):
		continue
	print(extractName)
	extractID=registered["Extract"][extractName]
	r=requests.get(url+"/samples/"+extractID,headers=headers2)
	if BadRequest(r,200):
		r.raise_for_status
	MR=requests.get(url+"/samples/"+extractID+"/meta",headers=headers2)
	if BadRequest(MR,200):
		MR.raise_for_status()
	PicFromE="NA"
	PicFromEwrongField="NA"
	IDforRemPic="NA"
	for meta in MR.json().get("data"):
		if meta.get("key") == "Pictures Drilling":
			PicFromE=meta.get("value")
		elif meta.get("key") == "Pictures":
			IDforRemPic=format(meta.get("sampleMetaID"))
			if not (meta.get("value") is  None or meta.get("value") ==""):
				PicFromEwrongField=meta.get("value")
			
	print(PicFromE+"--"+PicFromEwrongField)
	if PicFromEwrongField != "NA":
		PicFromE=PicFromEwrongField
	if IDforRemPic != "NA":
		print("remove....:\n"+url + "samples/"+extractID+"/meta/"+FeateLabExe["Pictures"]["ID"])
		MDR=requests.delete(url + "samples/"+extractID+"/meta/"+IDforRemPic, headers = headers2)
		if BadRequest(MDR,204):
			MDR.raise_for_status()


	#PicFromE=PicFromE.replace("NA ","")

	parent=format(r.json()["parentSampleID"])
	#print(extractName+" "+parent)
	PR=requests.get(url+"/samples/"+parent+"/meta",headers=headers2)
	if BadRequest(PR,200):
		PR.raise_for_status()
	PicFromSK="NA"
	for meta in PR.json().get("data"):
		if meta.get("key") == "Pictures Drilling":
			PicFromSK=meta.get("value")

	#PicFromSK=PicFromSK.replace("NA ","")
	if PicFromSK != PicFromE:
		print("1."+PicFromE+"@@\n2."+PicFromSK+"@@")
		if PicFromSK != "NA" and PicFromE == "NA":
			print("kept 2")
			prompt="2"

		elif PicFromE != "NA" and PicFromSK == "NA":
			prompt="1"
			print("kept 1")
		else:
			prompt="?"
			while prompt not in ["1","2"]:
				prompt=input("-->which(1 or 2)?")

		if prompt == "1":
			new=PicFromE
		elif prompt == "2":
			new=PicFromSK
		else:
			exit("what "+prompt+"?")
		MetaDataEx={"sampleTypeMetaID": int(FeateLabExe["Pictures Drilling"]['ID']),"sampleDataType": FeateLabExe["Pictures Drilling"]['TYPE'],"key": "Pictures Drilling","value": new}
		MDR=requests.put(url + "samples/"+extractID+"/meta", headers = headers2, data = MetaDataEx)
		if BadRequest(MDR,204):
			MDR.raise_for_status()
		MetaDataSK={"sampleTypeMetaID": int(FeateLabSkel["Pictures Drilling"]['ID']),"sampleDataType": FeateLabSkel["Pictures Drilling"]['TYPE'],"key": "Pictures Drilling","value": new}
		MDR=requests.put(url + "samples/"+parent+"/meta", headers = headers2,data = MetaDataSK)
		if BadRequest(MDR,204):
			MDR.raise_for_status()
	else:
		print(extractName+": same!\n1."+PicFromE+"@@\n2."+PicFromSK+"@@")