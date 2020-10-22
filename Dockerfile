FROM python:3.7-slim
RUN apt-get update && apt-get upgrade -y && apt-get install -y gcc build-essential curl cron
RUN pip install --upgrade pip
# All the services that use this image should expect common to be in /usr/app/common
WORKDIR /usr/app

# install requirements
COPY ./requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# TEST '1294611534:AAHtL9_ELo_JfsITp2JYlxXWZr_isrn2M-k'
# PROD '1354987324:AAEEqmaZ1MQFe17UAxmpijtv6ujqzl8DyPw'
ENV TOKEN='1354987324:AAEEqmaZ1MQFe17UAxmpijtv6ujqzl8DyPw'
# my id '274486566'
# id teacher '164960798'
ENV ADMINS='164960798'
ENV DEV=0
# add app
COPY . .

# Run server
CMD ["python3", "-u", "main.py"]