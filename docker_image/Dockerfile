FROM python:3.10

ARG tempFiles=files
ARG distPrefix=panos_upgrade_assurance

WORKDIR /tmp/prereqs
COPY ${tempFiles}/requirements.txt ./
COPY ${tempFiles}/${distPrefix}* ./
RUN python -m pip install -r requirements.txt
RUN python -m pip install ${distPrefix}*.tar.gz

WORKDIR /
RUN rm -rf /tmp/prereqs
