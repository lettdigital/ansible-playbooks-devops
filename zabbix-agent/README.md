Role Name
=========

Installs zabbix agent on host and configures the EC2 seucrity group so it is
discoverable.

Requirements
------------

EC2 full access permissions on the machine running the ansible role.

Role Variables
--------------

Private ip, ssh key and user name

Dependencies
------------

* boto3

Example
----------------

## Single host
```shell script
ansible -v $HOST_PRIVATE_IP -i $HOST_PRIVATE_IP, \
  --user=$HOST_USER \
  --key-file=$HOST_PRIVATE_KEY \
  --module-name=import_role --args name=zabbix-agent
```

## Multiple hosts

```shell script
pipenv run python install_on_all_ec2.py
```

It will ignore all ec2 created by beanstalk environments.

License
-------

All rights reserved

Author Information
------------------

Gabriel Chamon Araujo, 05/11/2020
