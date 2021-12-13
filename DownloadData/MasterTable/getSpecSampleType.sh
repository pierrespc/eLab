#!/bin/bash

table=$1
st=$2 ###separated by a ","

#sed -i s/|//g $table
awk -v s="$st" -F "\t" 'BEGIN{num=0; split(s,listS,",")} {if(NR==1){for(i=1;i<=NF;i=i+1){for(key in listS){if(match($i,listS[key])){num=num+1;col[num]=i}}}};for(i=1;i<=num;i=i+1){colN=col[i]; printf "%s\t", $colN}; print ""}' $table | awk -F "\t" -v s="$st" -v OFS="\t" '{if($1!="NA")print $0}' | uniq 


