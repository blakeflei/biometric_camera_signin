#!/bin/bash

# Add local user if not exist
USER_ID=${LOCAL_USER_ID:-1000}
USER_NAME=${LOCAL_USER_NAME:-"biom"}
id -u ${USER_NAME} > /dev/null 2>&1 
if [[ $? -eq 1 ]]; then
  groupadd ${USER_NAME} \
	  -r \
  	  -g ${USER_ID} && \
  useradd -u ${USER_ID} \
  	-o \
  	-m ${USER_NAME} \
	-g ${USER_NAME}
  usermod -a -G video ${USER_NAME}
fi
export HOME=/home/${USER_NAME}

exec gosu ${USER_NAME} "$@"
