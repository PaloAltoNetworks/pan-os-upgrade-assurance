FROM python:3.10


WORKDIR /
COPY requirements.txt ./
COPY dist/panos_upgrade_assurance* ./
RUN python -m pip install -r requirements.txt
RUN python -m pip install panos_upgrade_assurance*.tar.gz
