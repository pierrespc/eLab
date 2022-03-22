#!/bin/bash


#colName="Skeleton Element"
file=$1
colName="$2"

echo $file
awk -F "\t" -v na="$colName" '{if(NR==1){for(i=1;i<=NF;i=i+1){if($i==na){col=i}}}else{print $col}}' $file

			



