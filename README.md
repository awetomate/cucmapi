# cucmapi

The cucmapi package is inspired by Levensailor's [ciscoaxl](https://github.com/levensailor/ciscoaxl), Presidio's [ciscoris](https://github.com/PresidioCode/ciscoris), and Jonathanelscpt's [ciscocucmapi](https://github.com/jonathanelscpt/ciscocucmapi).

cucmapi runs on [python-zeep](https://docs.python-zeep.org/en/master/) and offers a complete abstraction from the AXL SOAP API and XML.  
The package gives you access to all API calls defined in the WSDL file.  
Currently, only Python 3.6+ is supported.

While not Pythonic, I chose to keep all the method names as they are defined in the AXL schema reference, instead of turning them into snake-case variants, to have a 1:1 match between the available methods in this package and Cisco's documentation; i.e. if the WSDL operation is called addSipProfile then the method is called addSipProfile, too.  

## Official Cisco API Documentation

- AXL: https://developer.cisco.com/docs/axl-schema-reference/
- RisPort70 API: https://developer.cisco.com/docs/sxml/#!risport70-api-reference
- Control Center Services API: https://developer.cisco.com/docs/sxml/#!control-center-services-api-reference
- Log Collection API: https://developer.cisco.com/docs/sxml/#!log-collection-and-dimegetfileservice-api-reference
- CDRonDemand API: https://developer.cisco.com/docs/sxml/#!cdrondemand-api-reference
- PerfMon API: https://developer.cisco.com/docs/sxml/#!perfmon-api-reference

## Installation

```bash
git clone git@github.com:awetomate/cucmapi.git
```

Testing in a lab is highly recommended. You can reserve a DevNet [Sandbox](https://developer.cisco.com/site/sandbox/) free of charge!

___


## Enable AXL SOAP Service on CUCM:

Enable the AXL SOAP interface

Browse to the CUCM Serviceability page on https://<IP_CUCM>/ccmservice

Tools > Service Activation:

Enable the "Cisco AXL Web Service"
![](https://pubhub.devnetcloud.com/media/axl/docs/authentication/assets/activation.png#developer.cisco.com)

---

## Create an AXL Service Account

> Step 1 - Create an AXL User Group

CUCM > User Management > User Group > Add.

> Step 2 - Assign the AXL role to the group

On the top right drop down list "Related Links". 

Select "Assign Role to User Group" and 
- for full Read/Write access, select:
  "Standard AXL API Access" 
- for Read-Only access, select "Standard AXL API Users" and "Standard AXL Read Only API Access"

> Step 3 - Create a new Application User

CUCM > User Management > Application User > Add.

Add the new User Group you created in step 1 and 2 to this user.

## Quick Start
```python
from cucmapi import axl, ris, ccs, log, cdr, pfm

username = "username"
password = "supersecret"
cucm = "fqdn" #or IP address
cucm_version = "11.5"
AXL = axl(username=username, password=password, cucm=cucm, cucm_version=cucm_version) # for SOAP AXL
RIS = ris(username=username, password=password, cucm=cucm, cucm_version=cucm_version) # for RisPort70
CCS = ccs(username=username, password=password, cucm=cucm, cucm_version=cucm_version) # for Control Center Services
LOG = log(username=username, password=password, cucm=cucm, cucm_version=cucm_version) # for Log Collection
CDR = cdr(username=username, password=password, cucm=cucm, cucm_version=cucm_version) # for CDRonDemand
PFM = pfm(username=username, password=password, cucm=cucm, cucm_version=cucm_version) # for PerfMon

# get phone
phone = AXL.getPhone(name="CSFjohn")
print(phone.description)
>>>
Johns test description
>>>
# update phone description
AXL.updatePhone(name="CSFjohn", description="Johns proper phone description")
# verify the new description has been set
phone = AXL.getPhone(name="CSFjohn")
print(phone.description)
>>>
Johns proper phone description
>>>

# get phone registration from RIS > requires a list of devices as input and returns a list
# if no list of subscribers is provided, all nodes in the cluster are queried
reg = RIS.selectCmDeviceExt(devices=["CSFjohn"])
print(reg[0].Status)
>>>
Registered
>>>

# delete phone
AXL.removePhone(name="CSFjohn")

# implicit "return all" will all available returnedTags
# use sparingly and avoid on larger clusters (limit the returnedTags to what you need)
all_devices = AXL.listPhone()

```

```python
# Usecase Example 1: Find out if there are still some registered Cisco IP Communicators (end of support)

# Step 1, get process node names, exlude the entry called 'EnterpriseWideData' 
# This is optional. If you don't provide a list of subs in step3 all nodes in the cluster are queried
node_names = [node.name for node in AXL.listProcessNode(returnedTags={"name": ""}) if "Enterprise" not in node.name]

# Step 2, get a list of all Cisco IP Communicators via Thin SQL > returns list of dictionaries
cipcs = AXL.executeSQLQuery(sql="SELECT name FROM device WHERE tkclass=1 and tkmodel=30016")
device_names = [ipc["name"] for ipc in cipcs]

# Alternative to step 2 using axl
phone_list = AXL.listPhone(returnedTags={"name": "", "model": ""})
device_names = [phone.name for phone in phone_list if "Communicator" in phone.model]

# Step 3, find all 'Registered' devices via RIS
registration = RIS.selectCmDeviceExt(devices=device_names, subs=node_names, status="Registered")
# or
registration = RIS.selectCmDeviceExt(devices=device_names, status="Registered")

```

```python
# Usecase Example 2: Get services status for each node in the cluster

# Step 1, get the process node names plus the nodeUsage; exlude the entry called 'EnterpriseWideData' 
node_names = AXL.listProcessNode(returnedTags={"name": "","nodeUsage": ""})
nodes = [{"name": node.name, "nodeUsage": node.nodeUsage} for node in node_names if "Enterprise" not in node.name]

# Step 2, get the services info for each of the nodes and add them to the services list
services = []
for node in nodes:
    # create a Control Center Services client instance for each node
    CCS = ccs(username=username, password=password, cucm=node["name"], cucm_version=version)
    # get the services for the node
    services_status = CCS.soapGetServiceStatus()
    # Optional: create your own custom view and replace the ReasonCodes with 'Activated/Deactivated'
    services_clean = [
        {"ServerName": node["name"],
        "NodeType": node["nodeUsage"],
        "ServiceName": s.ServiceName,
        "ServiceStatus": s.ServiceStatus,
        "ActivationStatus": "Activated" if "Service Not Activated" not in s.ReasonCodeString else "Deactivated",
        "StartTime": "" if not s.StartTime else s.StartTime
        } for s in services_status]
    # add the node's services to the services list
    services += services_clean

# now you have a list of all services for each node in the cluster
print(services)
>>>
[{'ServerName': 'servernode01.domain.com',
  'NodeType': 'Subscriber',
  'ServiceName': 'A Cisco DB',
  'ServiceStatus': 'Started',
  'ActivationStatus': 'Activated',
  'StartTime': 'Sat Nov 20 18:40:52 2021'},
 {'ServerName': 'servernode01.domain.com',
  'NodeType': 'Subscriber',
  'ServiceName': 'A Cisco DB Replicator',
  'ServiceStatus': 'Started',
  'ActivationStatus': 'Activated',
  'StartTime': 'Sat Nov 20 18:40:53 2021'},
 {'ServerName': 'servernode01.domain.com',
  'NodeType': 'Subscriber',
  'ServiceName': 'Cisco AMC Service',
  'ServiceStatus': 'Started',
  'ActivationStatus': 'Activated',
  'StartTime': 'Sat Nov 20 18:41:53 2021'},
  ...
  ]
>>>
```
