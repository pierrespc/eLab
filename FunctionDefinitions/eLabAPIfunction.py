###check requests
def BadRequest(myReq,code=200):
    return(myReq.status_code !=code)



###to retrieve treeness of storages
def getParentSto(ID,stoDict):
    if stoDict[ID]["parentID"]==0:
        return(stoDict[ID]["name"])
    else:
        return(getParentSto(stoDict[ID]["parentID"],stoDict)+", "+stoDict[ID]["name"])


###function to replace an empty value read in elab by "nan"
def putNan(jsonRead,key):
	if jsonRead.get(key) is not None:
		return(format(jsonRead.get(key)).replace("\n","| "))
	else:
		return("nan")




###Check date is correctly formated
def CheckDate(Date):
    if Date =="?":
        return(False)
    else:
        tmp=Date.split("-")
        tmp=[int(i) for i in tmp]
        return(tmp[0] > 2020 and tmp[0] < 2030 and tmp[1] > 0 and tmp[1] < 13 and tmp[2] >0 and tmp[2]<32)


###get a date filter
def getDateFilter():
    wrongEntry=True
    while wrongEntry:
        MostRecent="?"
        while MostRecent != "9999-12-31" and not CheckDate(MostRecent):
            MostRecent=input("Enter the most recent date, i.e. we will filter IN samples before that date (type Any if no filter )")
            if MostRecent == "Any":
                MostRecent="9999-12-31"
        MostRecent=datetime.strptime(MostRecent,'%Y-%m-%d')
        Eldest="?"
        while Eldest != "0001-01-01" and not CheckDate(Eldest):
            Eldest=input("Enter the eldest date, i.e. i.e. we will filter IN samples after that date (type Any if no filter )")
            if Eldest == "Any":
                Eldest="0001-01-01"
        Eldest=datetime.strptime(Eldest,'%Y-%m-%d')
        if Eldest<MostRecent:
            wrongEntry=False
        else:
            print("you entered a mostRecent date more ancient and EldestDate")
            
    return({"MostRecent":MostRecent,"Eldest":Eldest})


##get a filter according to COMBO or dropdown
def getOptionFilter(possibleChoices):
    print(len(possibleChoices))
    wrongEntry=True
    while wrongEntry:
        print("possible choices")
        index=0
        for value in possibleChoices:
            index=index+1
            print(format(index)+":"+value)
        listEntered=input("enter your choice(s) (the number(s) separated by space)").split()
        listEntered=[int(i)-1 for i in listEntered ]
        if min(listEntered) <0 or max(listEntered)>=len(possibleChoices):
            print("you entered choices out of range")
        else:
            wrongEntry=False
    return([possibleChoices[i] for i in listEntered])


###for now we cover just the case where a given string is in the feature (no filter for NOT, OR, AND, NOT ANY, etc...)
def getTextFilter():
    return(input("enter a string to find in the field"))


###get a filter according to link to other samples
def getLinkFilter(sampleType,allIDs,link):
    parentPattern={"Site":{"pattern":"Any","typeParent":"None"},
                   "Individual":{"pattern":'[A][R][0-9][0-9][0-9][0-9]',"typeParent":"Site"},
                   "Skeleton Element":{"pattern":'[A][R][0-9][0-9][0-9][0-9][.][0-9]',"typeParent":"Individual"},
                   "Extract":{"pattern":'[A][R][0-9][0-9][0-9][0-9][.][0-9][.][0-9]',"typeParent":"Skeleton Element"}}

    if sampleType not in parentPattern.keys():
        raise(sampleType+" not covered to retrieve its parent sample")
    if link:
        typeToCheck=parentPattern[sampleType][typeParent]
    else:
        typeToCheck=sampleType
                   
    listType="?"
    while not listType in ["prompt","file"]:        
        listType=input("will you enter IDs one by one or a file (prompt/file)?")
    wrongEntry=True
    while wrongEntry:
        if listType=="file":
            listIDfile=open(input("file with parent file"),"r").readlines()
            listID=[]
            for i in listIDfile:
                listID.append(i.strip())
        else:
            listID=input("enter the parent sample IDs separated by <space>/<space>, must match pattern "+parentPattern[typeToCheck]["pattern"])
            listID=listID.split(" / ")
        wrongEntry=False
        for id in listID:
            ###check all id match pattern
            if not (re.match(parentPattern[typeToCheck]["pattern"],id) or parentPattern[typeToCheck]["pattern"] == "Any"):
                print("wrong pattern for "+id+" expected: "+parentPattern[typeToCheck]["pattern"])
                wrongEntry=True
                ###check all id already registered
            if not id in allIDs.keys():
                print(id+" not registered in eLab")
                wrongEntry=True
        if wrongEntry:
            print("change those ids either in the file or in the prompted list")
     
    bound="?"
    while bound not in ["notin","in"]:
        bound=input("keep or remove those IDS (in/notin)?")
    return({"rule":bound,"list":listID})


###filter according to quantity
def getQuantityFilter():
    wrongEntry=True
    while wrongEntry:
        quanti=float(input("enter a quantity"))
        bound=input("enter a bound (less, more, exact)")
        if bound in ["less","more","exact"]:
            wrongEntry=False
    return({"rule":bound,"quantity":quanti})




######
def filterText(value,filter):
    return(filter in value)

def filterQuantity(value,thres,ruler):
    if ruler == "exact":
        return(value==thres)
    elif ruler == "less":
        return(value<=thres)
    elif ruler == "more":
        return(value>=thres)
    else:
        raise(ruler+ " not recognized")

def filterDate(value,filter):
    value=datetime.strptime(value,'%Y-%m-%d')
    return(value<=filter["MostRecent"] and value>=filter["Eldest"])

def filterLink(value,listNAM,ruler):
    value=value.split("|")[0]
    if ruler=="in":
        return(value in listNAM)
    elif ruler=="notin":
        return(value not in listNAM)
    else:
        raise()

        
def filterName(value,listNAM,ruler):
    if ruler=="in":
        return(value in listNAM)
    elif ruler=="notin":
        return(value not in listNAM)
    else:
        raise()
    

def filterCombo(value,filter):
    return(value in filter)

def filterCheckbox(value,filter):
    AllFound=True
    for i in value:
        if i not in filter:
            AllFound=False
    return(AllFound)
