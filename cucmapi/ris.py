import re
import requests
import urllib3
from pathlib import Path
from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client, Settings
from zeep.cache import SqliteCache
from zeep.exceptions import Fault
from zeep.transports import Transport


class ris(object):
    """
    The RisPort70 class sets up the connection to the call manager with methods for retrieving RIS data
    Tested with Python 3.8.10 and 3.9.5
    """

    def __init__(self, username, password, cucm, cucm_version):
        """
		:param username: axl username
		:param password: axl password
		:param cucm: fqdn or IP address of CUCM
		:param cucm_version: CUCM version
		"""

        wsdl = f"https://{cucm}:8443/realtimeservice2/services/RISService70?wsdl"

        # create a session
        session = Session()

        # disable certificate verification and insecure request warnings
        session.verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        requests.packages.urllib3.disable_warnings( )

        # to enable SSL cert verification, copy the CUCM tomcat .pem file and uncomment the following lines
        # CERT = 'cucmtomcat.pem'
        # session.verify = CERT

        session.auth = HTTPBasicAuth(username, password)
        transport = Transport(session=session, timeout=10, cache=SqliteCache())
        settings = Settings(strict=False, xml_huge_tree=True, xsd_ignore_sequence_order=True) 
        ris_client = Client(wsdl, settings=settings, transport=transport) 

        self.wsdl = wsdl
        self.username = username
        self.password = password
        self.cucm = cucm
        self.cucm_version = cucm_version
        self.UUID_PATTERN = re.compile(r"^[\da-f]{8}-([\da-f]{4}-){3}[\da-f]{12}$", re.IGNORECASE)
        self.client = ris_client.create_service("{http://schemas.cisco.com/ast/soap}RisBinding", f"https://{cucm}:8443/realtimeservice2/services/RISService70")


    def get_cm_device_ext(self, **args):
        """
        Runner function to get registration information using the 
        SelectCMDeviceExt method from the RisPort70 API. 
        This function is called by and gets its arguments from 'selectCmDeviceExt()'

        To call this function directly, the entire CmSelectionCriteria SOAP 
        request body needs to be provided as argument.
        https://developer.cisco.com/docs/sxml/#!risport70-api-reference/selectcmdeviceext
        """
        try:
            output = self.client.selectCmDeviceExt("", args)
            state_info = output["StateInfo"]
            return_value = output["SelectCmDeviceResult"]
            return return_value, state_info
            #return self.client.selectCmDeviceExt("", args)['SelectCmDeviceResult']
        except Fault as e:
            return e

    def get_cti_item(self, **args):
        """
        WORK IN PROGRESS - I don't fully understand how to use this method yet.

        Runner function to get CTI Manager related information using the 
        SelectCtiItem method from the RisPort70 API. 
        This function is called by and gets its arguments from 'selectCtiItem()'

        To call this function directly, the entire CmSelectionCriteria SOAP 
        request body needs to be provided as argument.
        https://developer.cisco.com/docs/sxml/#!risport70-api-reference/selectctiitem
        """
        try:
            return self.client.selectCtiItem("", args)["SelectCmDeviceResult"]
        except Fault as e:
            print(e)
            return e

    def selectCmDeviceExt(self, devices, subs, device_class="Phone", status="Any"):
        """
        Get registration information for various device types using the 
        SelectCMDeviceExt method from the RisPort70 API.
        TODO: Implement StateInfo usage

        :param devices: list of devices to check the registration info for
        :param subs: list of call processing subscribers to check against or None (=all nodes)
        :param device_class: target device type. Defaults to "Phone"
        :param status: target device registration status. Defaults to "Any"
        :return: result list

        Input values for device_class:
            "Any", "Phone", "Gateway", "H323", "Cti", "VoiceMail", 
            "MediaResources", "HuntList", "SIPTrunk", "Unknown"
        
        Input values for status:
            "Any", "Registered", "UnRegistered", "Rejected", 
            "PartiallyRegistered", "Unknown"
        """

        def parse(output):
            """
            This parser function extracts all the device information from the 
            SelectCMDeviceExt method's response. It will create a list containing
            dictionaries for each device
            """
            devices = []
            if output['CmNodes'] is not None:
                for node in output.CmNodes.item:
                    for device in node.CmDevices.item:
                        devices.append(device)
                return devices
            else: 
                return
        
        def limit(devices, n=1000): 
            """
            this function turns large phone lists into chunks of 1000
            """
            return [devices[i: i + n] for i in range(0, len(devices), n)]

        # define available device classes as per API documentation
        # https://developer.cisco.com/docs/sxml/#!risport70-api-reference/selectcmdevice
        device_classes = (
                "Any", "Phone", "Gateway", "H323", "Cti", "VoiceMail", 
                "MediaResources", "HuntList", "SIPTrunk", "Unknown"
        )
        # define available status values as per API documentation
        # https://developer.cisco.com/docs/sxml/#!risport70-api-reference/selectcmdevice
        state_values = (
                "Any", "Registered", "UnRegistered", "Rejected", 
                "PartiallyRegistered", "Unknown"
        )
        # prepare request SOAP body to send to CUCM using zeep
        CmSelectionCriteria = {
            "MaxReturnedDevices": "1000",
            "DeviceClass": "",
            "Model": 255,
            "Status": "",
            "NodeName": "",
            "SelectBy": "Name",
            "SelectItems": {
                "item": {
                    "Item": ""
                }
            },
            "Protocol": "Any",
            "DownloadStatus": "Any"
        }
        # update DeviceClass in SOAP body and raise exception if content is invalid
        if device_class in device_classes:
            CmSelectionCriteria["DeviceClass"] = device_class
        else:
            raise ValueError(f"device_class needs to contain one of the following:\n{device_classes}")    
        # update Status in SOAP body and raise exception if content is invalid
        if status in state_values:
            CmSelectionCriteria['Status'] = status
        else:
            raise ValueError(f"status needs to contain of the following:\n{state_values}")

        # prepare return object (list) for later
        registered = []
        # divide device list into chucks of 1000 - only relevant if +1000 devices
        groups = limit(devices)

        for group in groups:
        # loop through Subscrbers and retrieve registration information for all devices
            if subs:
                for sub in subs:
                    # update NodeName in SOAP body with Subscriber's name
                    CmSelectionCriteria['NodeName'] = sub
                    # add all devices of the current group to the SOAP body
                    CmSelectionCriteria['SelectItems']['item']['Item'] = ",".join(group)
                    output_raw, state_info = self.get_cm_device_ext(**CmSelectionCriteria)
                    # if there are no devices in the ouput - skip
                    # otherwise, send output to the parser function and return clean ouput
                    if output_raw['TotalDevicesFound'] <1:
                        continue
                    else:
                        output = parse(output_raw)
                    registered.extend(output)
            else:
                # update NodeName in SOAP body with Subscriber's name
                CmSelectionCriteria['NodeName'] = None
                # add all devices of the current group to the SOAP body
                CmSelectionCriteria['SelectItems']['item']['Item'] = ",".join(group)
                output_raw, state_info = self.get_cm_device_ext(**CmSelectionCriteria)
                # if there are no devices in the ouput - skip
                # otherwise, send output to the parser function and return clean ouput
                if output_raw['TotalDevicesFound'] <1:
                    continue
                else:
                    output = parse(output_raw)
                registered.extend(output)
        
        return registered

    def selectCtiItem(self, devices, subs, cti_mgr_class="Line", status="Any"):
        """
        WORK IN PROGRESS - I don't fully understand how to use this method yet.
        """

        def parse(output):
            """
            This parser function extracts all the device information from the 
            SelectCtiItem method's response. It will create a list containing
            dictionaries for each device
            """
            devices = []
            if output['CtiNodes'] is not None:
                for node in output.CtiNodes.item:
                    for device in node.CtiItems.item:
                        devices.append(device)
                return devices
            else: 
                return

        # define available CtiMgrClass values as per API documentation
        # https://developer.cisco.com/docs/sxml/#!risport70-api-reference/selectctiitem
        cti_mgr_classes = ("Provider", "Device", "Line")

        # define available status values as per API documentation
        # https://developer.cisco.com/docs/sxml/#!risport70-api-reference/selectctiitem
        state_values = ("Any", "Open", "Closed", "OpenFailed", "Unknown")
        
        # prepare return object (list) for later
        cti_status = []

        CtiSelectionCriteria = {
            "MaxReturnedDevices": "1000",
            "CtiMgrClass": "Device",
            "Status": "Any",
            "NodeName": "",
            "SelectAppBy": "AppId",
            "AppItems": {
                "item": {
                    "AppItem": ""
                }
            },
            "DevNames": {
                "item": {
                    "DevName": ""
                }
            },
            "DirNumbers": {
                "item": {
                    "DirNumber": ""
                }
            },
        }
        # update DeviceClass in SOAP body and raise exception if content is invalid
        if cti_mgr_class in cti_mgr_classes:
            CtiSelectionCriteria["CtiMgrClass"] = cti_mgr_class
        else:
            raise ValueError(f"cit_mgr_class needs to contain one of the following:\n{cti_mgr_classes}")    
        # update Status in SOAP body and raise exception if content is invalid
        if status in state_values:
            CtiSelectionCriteria['Status'] = status
        else:
            raise ValueError(f"status needs to contain of the following:\n{state_values}")

        # loop through Subscrbers and retrieve registration information for all devices
        for sub in subs:
            # update NodeName in SOAP body with Subscriber's name
            CtiSelectionCriteria['NodeName'] = sub
            # add all devices to the SOAP body
            CtiSelectionCriteria['DevNames']['item']['DevName'] = ",".join(devices)
            output_raw, state_info = self.get_cti_item(**CtiSelectionCriteria)
            # if there are not devices in the ouput - skip
            # otherwise, send output to the parser function and return clean ouput
            if output_raw['TotalDevicesFound'] <1:
                continue
            else:
                output = parse(output_raw)
            cti_status.extend(output)

        return cti_status, state_info
