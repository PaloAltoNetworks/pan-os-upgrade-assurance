#!/bin/bash

DIST_PREFIX=panos_upgrade_assurance
TEMP_FILES=files

if [ -d ${TEMP_FILES} ]; then rm ${TEMP_FILES}/*
else mkdir ${TEMP_FILES}
fi

# generate requirements.txt file 
poetry export --without-hashes --format=requirements.txt > ${TEMP_FILES}/requirements.txt

# build the latest libraries
rm ../dist/${DIST_PREFIX}*
poetry build

# copy over the built package
cp ../dist/${DIST_PREFIX}* ./${TEMP_FILES}

# copy over all example scripts
find ../examples -name \*.py -exec cp '{}' ./${TEMP_FILES} \;

# build the image
docker build -t ${DIST_PREFIX}:$(poetry version -s) .
