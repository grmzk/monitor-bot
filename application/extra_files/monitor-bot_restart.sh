#!/bin/bash


/usr/bin/docker-compose --project-directory /home/BSMP1/potrav2/.monitor-bot/infra/ --file /home/BSMP1/potrav2/.monitor-bot/infra/docker-compose.yml --project-name monitor-bot down
/usr/bin/docker-compose --project-directory /home/BSMP1/potrav2/.monitor-bot/infra/ --file /home/BSMP1/potrav2/.monitor-bot/infra/docker-compose.yml --project-name monitor-bot up --build -d
