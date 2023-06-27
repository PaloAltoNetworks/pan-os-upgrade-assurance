#!/bin/bash

if [ "$IMAGE_PREFIX" ]; then 
  echo "Building the image under the custom name: ${IMAGE_PREFIX}"
else
  echo "Building the image under the default name: panos_upgrade_assurance"
fi

DIST_PREFIX=panos_upgrade_assurance
IMAGE_PREFIX="${IMAGE_PREFIX:-panos_upgrade_assurance}" 
TEMP_FILES=$(dirname $0)/files

if [ -d ${TEMP_FILES} ]; then rm -f ${TEMP_FILES}/*
else mkdir ${TEMP_FILES}
fi

# generate requirements.txt file 
poetry export --without-hashes --format=requirements.txt > ${TEMP_FILES}/requirements.txt

# build the latest libraries
rm -f $(dirname $0)/../dist/${DIST_PREFIX}*
poetry build

# copy over the built package
cp $(dirname $0)/../dist/${DIST_PREFIX}* ./${TEMP_FILES}

# build the image
docker build -f $(dirname $0)/Dockerfile -t ${IMAGE_PREFIX}:$(poetry version -s) $(dirname $0)
