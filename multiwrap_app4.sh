#!/bin/bash
set -a 

loc_exp=(
ca547
ca548
ca587
ch097
)

MODE=production
for exp in ${loc_exp[@]}; do
  #./production_app4.sh $exp
  ./check_app4.sh $exp
  #./production_qc4.sh $exp
  #break
done
exit

