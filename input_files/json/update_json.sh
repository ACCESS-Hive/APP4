#!/bin/bash
echo "updating version date...${datevers}"
scriptpath="$( cd "$(dirname "$0")" ; pwd -P )"
echo $scriptpath
cd $scriptpath

if [ $MODE == default ]; then
  if [ $VERSION == CM2 ]; then
    json=default_cm2.json
  elif [ $VERSION == ESM ]; then
    json=default_esm.json
  else
    echo "default jsons only exist for CM2 and ESM thus far"
  fi
else
  json=${EXP_TO_PROCESS}.json
fi
echo $json
dateline="    \"version\":                      \"v${datevers}\","
if [ $MODE == ccmi ]; then 
  maindirline="    \"outpath\":                      \"${DATA_DIR}/APP_output/CCMI2022\","
elif [ $MODE == default ]; then
  maindirline="    \"outpath\":                      \"${DATA_DIR}/CMORised_output\","
else
  maindirline="    \"outpath\":                      \"${DATA_DIR}/APP_output/CMIP6\","
fi

vline=$(grep '\"version\":' $json)
outpathline=$(grep '\"outpath\":' $json)
sed -i "s@${vline}@${dateline}@g" $json
sed -i "s@${outpathline}@${maindirline}@g" $json
