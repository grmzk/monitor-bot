#!/bin/bash


/usr/bin/docker compose --project-directory ~/.monitor-bot/infra/ \
                        --file ~/.monitor-bot/infra/docker-compose.yml \
                        --project-name monitor-bot \
                        down
/usr/bin/docker compose --project-directory ~/.monitor-bot/infra/ \
                        --file ~/.monitor-bot/infra/docker-compose.yml \
                        --project-name monitor-bot \
                        up --build -d
