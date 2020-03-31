zabbix-agent
=========

Installs zabbix agent on host.

Requirements
------------

EC2 full access permissions on the machine running the ansible role.

Role Variables
--------------

Private ip, ssh key and user name

Example
----------------

## Single host
```shell script
ansible -v $HOST_PRIVATE_IP -i $HOST_PRIVATE_IP, \
  --user=$HOST_USER \
  --key-file=$HOST_PRIVATE_KEY \
  --extra-vars="zabbix_major_version=$ZABBIX_MAJOR_VERSION" \
  --module-name=import_role --args name=zabbix-agent
```

## Automatic EC2 Discovery

### Requisites

* boto3

* An s3 bucket containing the necessary ssl keys for ssh connection.

### Configuration

The configuration is done by environment variables

| Environment Variable       | Description                                         |
|----------------------------|-----------------------------------------------------|
| ZABBIX_SERVER              | Zabbix Server URL (format https://myzabbix.address) |
| ZABBIX_AUTOMATION_USER     | Zabbix User to connect to Server                    |
| ZABBIX_AUTOMATION_PASSWORD | Zabbix User password                                |
| SSL_KEYS_BUCKET            | S3 bucket from which to download the SSL keys       |

By default all EC2 except those created by Elastic Beanstalk environments will be
targeted. To disable installation on a single EC2, add the following tag to it: `disable_zabbix_agent_installation: true`

### Example

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
