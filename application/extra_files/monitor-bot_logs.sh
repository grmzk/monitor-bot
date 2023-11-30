#!/bin/bash


if [ -z $1 ] ; then
    SINCE="$(date +%Y-%m-%d --utc)T00:00:00.000000000Z"
    docker logs monitor-bot_application_1 -t --since $SINCE
else
    #SINCE="2023-10-14T21:36:48.917913491Z"
    SINCE="${1}T00:00:00.000000000Z"
    docker logs monitor-bot_application_1 -t --since $SINCE
fi
