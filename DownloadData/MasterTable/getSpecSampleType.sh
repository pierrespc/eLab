#!/bin/bash

table=$1
st=$2

awk -v s="$st" -F "\t" 'BEGIN{num=0; } {if(NR==1){for(i=1;i<=NF;i=i+1){if(match($i,s)){num=num+1;col[num]=i}}};for(i=1;i<=num;i=i+1){colN=col[i]; printf "%s\t", $colN}; print ""}' $table


