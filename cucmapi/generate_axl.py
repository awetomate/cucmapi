import os
from zeep import Client
from pathlib import Path


CUCM_VERSION = "11.5"

def load_wsdl_file(cucm_version):
    cwd = os.path.dirname(os.path.abspath(__file__))
    if os.name == "posix":
        wsdl = Path(f"{cwd}/schema/{cucm_version}/AXLAPI.wsdl").as_uri()
    else:
        wsdl = str(Path(f"{cwd}/schema/{cucm_version}/AXLAPI.wsdl").absolute())
    return Client(wsdl)


def create_client(cucm_version):
    client = load_wsdl_file(cucm_version)
    return client


def parse_elements(elements):
# source: https://stackoverflow.com/questions/50089400/introspecting-a-wsdl-with-python-zeep
    all_elements = {}
    for name, element in elements:
        all_elements[name] = {}
        all_elements[name]['optional'] = element.is_optional
        if hasattr(element.type, 'elements'):
            all_elements[name]['type'] = parse_elements(
                element.type.elements)
        else:
            all_elements[name]['type'] = str(element.type)
    return all_elements


def parse_service_interfaces(client):
# source: https://stackoverflow.com/questions/50089400/introspecting-a-wsdl-with-python-zeep
    interface = {}
    for service in client.wsdl.services.values():
        interface[service.name] = {}
        for port in service.ports.values():
            interface[service.name][port.name] = {}
            operations = {}
            for operation in port.binding._operations.values():
                operations[operation.name] = {}
                operations[operation.name]['input'] = {}
                elements = operation.input.body.type.elements
                operations[operation.name]['input'] = parse_elements(elements)
            interface[service.name][port.name]['operations'] = operations
    return interface


def write_imports():
    text = '''import os
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
'''
    return text


def write_class():
    text = '''
class axl(object):
    """
    This class creates the SOAP interface to interact with Cisco Unified Communciations Manager.
    The class methods were created with the WSDL file for CUCM release 11.5.
    Tested with Python 3.8.10.
    """

    def __init__(self, username, password, cucm, cucm_version):
        """
        :param username: axl username
        :param password: axl password
        :param cucm: fqdn or IP address of CUCM
        :param cucm_version: CUCM version
        """

        cwd = os.path.dirname(os.path.abspath(__file__))
        if os.name == "posix":
            wsdl = Path(f"{cwd}/schema/{cucm_version}/AXLAPI.wsdl").as_uri()
        else:
            wsdl = str(Path(f"{cwd}/schema/{cucm_version}/AXLAPI.wsdl").absolute())

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
        
        axl_client = Client(wsdl, settings=settings, transport=transport)

        self.wsdl = wsdl
        self.username = username
        self.password = password
        self.cucm = cucm
        self.cucm_version = cucm_version
        self.UUID_PATTERN = re.compile(
            r"^[\da-f]{8}-([\da-f]{4}-){3}[\da-f]{12}$", re.IGNORECASE
        )
        self.client = axl_client.create_service(
            "{http://www.cisco.com/AXLAPIService/}AXLAPIBinding",
            f"https://{cucm}:8443/axl/",
        )
'''
    return text


types = ['anyType(value)',
    'zeep.xsd.types.any.AnyType',
    'Name128(value)', 
    'Name50(value)',
    'String(value)', 
    'String10(value)', 
    'String100(value)', 
    'String1024(value)', 
    'String128(value)', 
    'String129(value)', 
    'String15(value)', 
    'String16(value)', 
    'String200(value)', 
    'String2048(value)', 
    'String255(value)', 
    'String32(value)', 
    'String4096(value)', 
    'String50(value)', 
    'String64(value)', 
    'String75(value)', 
    'UniqueName128(value)', 
    'UniqueName50(value)', 
    'UniqueString128(value)', 
    'UniqueString255(value)', 
    'UniqueString50(value)', 
    'XMacAddress(value)', 
    'XUUID(value)', 
    'boolean(value)', 
    'ENTITIES(value)', 
    'ENTITY(value)', 
    'ID(value)', 
    'IDREF(value)', 
    'IDREFS(value)', 
    'NCName(value)', 
    'NMTOKEN(value)', 
    'NMTOKENS(value)', 
    'NOTATION(value)', 
    'Name(value)', 
    'QName(value)', 
    'anySimpleType(value)', 
    'anyURI(value)', 
    'base64Binary(value)', 
    'Boolean(value)', 
    'Byte(value)', 
    'Date(value)', 
    'DateTime(value)', 
    'Decimal(value)', 
    'Double(value)', 
    'Duration(value)', 
    'Float(value)', 
    'gDay(value)', 
    'gMonth(value)', 
    'gMonthDay(value)', 
    'gYear(value)', 
    'gYearMonth(value)', 
    'HexBinary(value)', 
    'Int(value)', 
    'Integer(value)', 
    'Language(value)', 
    'Long(value)', 
    'NegativeInteger(value)', 
    'NonNegativeInteger(value)', 
    'NonPositiveInteger(value)', 
    'NormalizedString(value)', 
    'PositiveInteger(value)', 
    'Short(value)',
    'Time(value)', 
    'Token(value)', 
    'UnsignedByte(value)', 
    'UnsignedInt(value)', 
    'UnsignedLong(value)', 
    'UnsignedShort(value)',
    'UnionType(value)',
    'pin(value)',
    'XRequestTimeout(value)',
    'XRetryCount(value)']


def main():
    cwd = os.path.dirname(os.path.abspath(__file__))
    axl_file = os.path.join(cwd, "axl.py")
    client = create_client(CUCM_VERSION)
    interface = parse_service_interfaces(client)

    all_operations = [op for op in interface['AXLAPIService']['AXLPort']['operations'].keys()]

    with open(axl_file, "w") as f:
        #'write' the import to the file
        print(write_imports(), file=f)
        # 'write' class to the file
        print(write_class(), file=f)

        for i in all_operations:
            #get element group name - used for unpacking the result object of (most) 'get' and 'list' operations
            pos = [idx for idx in range(len(i)) if i[idx].isupper()][0] #find position of first capitalized letter
            element = i[pos:] #extract element group name
            element = element[0].lower()+element[1:] #turn first letter into lowercase
            
            # get parameters for each operation - used for creating the docstrings
            param = []
            for k in interface['AXLAPIService']['AXLPort']['operations'][i]['input'].keys():
                if interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'] in types:
                    if interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['optional'] ==  True:
                        param.append(f"        :param {k}: {interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type']}, optional")
                    else:
                        param.append(f"        :param {k}: {interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type']}")
                else:
                    if interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['optional'] ==  True:
                        param.append(f"        :param {k}: optional")
                    else:
                        param.append(f"        :param {k}: ")
                    for l in interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'].keys():
                            if "<zeep.xsd.types.any.AnyType object" in interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type']:
                                if interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['optional'] ==  True:
                                    param.append(f"            {l}: AnyType, optional")
                                else:
                                    param.append(f"            {l}: AnyType")
                            elif interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'] in types:
                                if interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['optional'] ==  True:
                                    param.append(f"            {l}: {interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type']}, optional")
                                else:
                                    param.append(f"            {l}: {interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type']}")
                            else:
                                if interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['optional'] ==  True:
                                    param.append(f"            {l}: optional")
                                else:
                                    param.append(f"            {l}: ")
                                for m in interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'].keys():
                                    if "<zeep.xsd.types.any.AnyType object" in interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['type']:
                                        if interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['optional'] ==  True:
                                            param.append(f"                {m}: AnyType, optional")
                                        else:
                                            param.append(f"                {m}: AnyType")
                                    elif interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['type'] in types:
                                        if interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['optional'] ==  True:
                                            param.append(f"                {m}: {interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['type']}, optional")
                                        else:
                                            param.append(f"                {m}: {interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['type']}")
                                    else:
                                        for n in interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['type'].keys():
                                            if "<zeep.xsd.types.any.AnyType object" in interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['type'][n]['type']:
                                                if interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['type'][n]['optional'] ==  True:
                                                    param.append(f"                    {n}: AnyType, optional")
                                                else:
                                                    param.append(f"                    {n}: AnyType")
                                            elif interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['type'][n]['type'] in types:
                                                if interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['type'][n]['optional'] ==  True:
                                                    param.append(f"                    {n}: {interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['type'][n]['type']}, optional")
                                                else:
                                                    param.append(f"                    {n}: {interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['type'][n]['type']}")
            # get input arguments of operation and create a list of dictionaries
            arguments = []
            for k in interface['AXLAPIService']['AXLPort']['operations'][i]['input'].keys():
                newk = {}
                if interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'] in types:
                    newk[k] = ""
                    arguments.append(newk)
                else:
                    newk[k] = {}
                    for l in interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'].keys():
                        if "<zeep.xsd.types.any.AnyType object" in interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type']:
                            newk[k][l] = ""
                        elif interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'] in types:
                            newk[k][l] = ""
                        else:
                            newk[k][l] = {}
                            for m in interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'].keys():
                                if "<zeep.xsd.types.any.AnyType object" in interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['type']:
                                    newk[k][l][m] = ""
                                elif interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][l]['type'][m]['type'] in types:
                                    newk[k][l][m] = ""
                    arguments.append(newk)
            # customize the arguments for the different operation types (add, get, list, etc.)
            axl_args = []
            tags = {}
            for a in arguments:
                # extract all available returnedTags and store them separately
                if "returnedTags" in a:
                    tags = a
                # customize 'list' operations
                if i.startswith("list"):
                    for k in a.keys():
                        # use all returnedTags by default
                        if "returnedTags" in k:
                            axl_args.append("returnedTags=returnedTags")
                        # force searchCriteria to '%', thus always returning all values
                        elif "searchCriteria" in k:
                            for n in a[k].keys():
                                a[k][n]="%"
                            axl_args.append(f'{a[k]}')
                        elif a[k]=="":
                            axl_args.append(f'{k}={k}')
                        else:
                            axl_args.append(f'{list(a.keys())[0]}={list(a.values())[0]}')
                # customize 'add' operations
                elif i.startswith("add"):
                    for k in a.keys():
                        if a[k]=="":
                            axl_args.append(f'{k}={k}')
                        else:
                            for n in list(a.values())[0]:
                                # fix issue in Python with AXL operations with values called 'class'
                                # replace the variable names with 'classvalue' in Python, 
                                # but still keep the dict key name as 'class' to send the correct name to AXL
                                if n=="class":
                                    axl_args.append(f'"{n}": {n}value') 
                                else:
                                    axl_args.append(f'"{n}": {n}')         
                # customize 'update' operations
                elif i.startswith("update"):
                    for k in a.keys():
                        # only explicitly add mandatory parameters to the method 
                        # additional **kwargs will be added later in the script
                        if interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['optional'] ==  False:
                            axl_args.append(f'{k}={k}')
                elif i.startswith("remove"):
                    for k in a.keys():
                        if a[k]=="":
                            axl_args.append(f'{k}={k}')
                        else:
                            axl_args.append(f'{list(a.keys())[0]}={list(a.values())[0]}')
                elif i.startswith("do"):
                    for k in a.keys():
                        if a[k]=="":
                            axl_args.append(f'{k}={k}')
                        elif "_value_1" in a[k]:
                            axl_args.append(f'{k}={k}')
                        else:
                            axl_args.append(f'{list(a.keys())[0]}={list(a.values())[0]}')
                elif i.startswith("apply"):
                    for k in a.keys():
                        if a[k]=="":
                            axl_args.append(f'{k}={k}')
                        else:
                            axl_args.append(f'{list(a.keys())[0]}={list(a.values())[0]}')
                elif i.startswith("restart"):
                    for k in a.keys():
                        if a[k]=="":
                            axl_args.append(f'{k}={k}')
                        else:
                            axl_args.append(f'{list(a.keys())[0]}={list(a.values())[0]}')
                elif i.startswith("reset"):
                    for k in a.keys():
                        if a[k]=="":
                            axl_args.append(f'{k}={k}')
                        else:
                            axl_args.append(f'{list(a.keys())[0]}={list(a.values())[0]}')
                elif i.startswith("lock"):
                    for k in a.keys():
                        if a[k]=="":
                            axl_args.append(f'{k}={k}')
                        else:
                            axl_args.append(f'{list(a.keys())[0]}={list(a.values())[0]}')
                elif i.startswith("wipe"):
                    for k in a.keys():
                        if a[k]=="":
                            axl_args.append(f'{k}={k}')
                        else:
                            axl_args.append(f'{list(a.keys())[0]}={list(a.values())[0]}')
                elif i.startswith("assign"):
                    for k in a.keys():
                        if a[k]=="":
                            axl_args.append(f'{k}={k}')
                        else:
                            axl_args.append(f'{list(a.keys())[0]}={list(a.values())[0]}')
                elif i.startswith("unassign"):
                    for k in a.keys():
                        if a[k]=="":
                            axl_args.append(f'{k}={k}')
                        else:
                            axl_args.append(f'{list(a.keys())[0]}={list(a.values())[0]}')
                elif i.startswith("execute"):
                    for k in a.keys():
                        if a[k]=="":
                            axl_args.append(f'{k}={k}')
                        else:
                            axl_args.append(f'{list(a.keys())[0]}={list(a.values())[0]}')
                else:
                    axl_args.append(f'{list(a.keys())[0]}={list(a.values())[0]}')
            # create a custom list of arguments for the method
            # get list of top-level parameters excl. searchCriteria
            args_reduced = [l for l in list(interface['AXLAPIService']['AXLPort']['operations'][i]['input'].keys()) if "searchCriteria" not in l]
            args_new = []
            # special treatment for the getNumDevices operation
            if i.startswith("getNumDevices"):
                args_new.append('deviceclass=""')
            # for 'get' operations simply write **kwargs
            # these operations will return all returnedTags by default
            elif i.startswith("get"):
                args_new.append('**kwargs')
            # special treatment for the listChange operation
            # ensures the first call of the operation is successful
            elif i.startswith("listChange"):
                args_new.append('startChangeId=None')
            # for 'add' operations list all mandatory arguments only
            elif i.startswith("add"):
                for k in interface['AXLAPIService']['AXLPort']['operations'][i]['input'].keys():
                    for m in interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'].keys():
                        if interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['type'][m]['optional'] ==  False:
                            if m=="class":
                                args_new.append(f'{m}value=""')
                            else:
                                args_new.append(f'{m}=""')
                        else:
                            # fix issue in Python with AXL operations with values called 'class'
                            # replace the variable names with 'classvalue'
                            if m=="class":
                                args_new.append(f'{m}value=None')
                            else:
                                args_new.append(f'{m}=None')
            # for 'update' operations list all mandatory arguments only, and add **kwargs at the end
            elif i.startswith("update"):
                for k in interface['AXLAPIService']['AXLPort']['operations'][i]['input'].keys():
                    if interface['AXLAPIService']['AXLPort']['operations'][i]['input'][k]['optional'] ==  False:
                        args_new.append(f'{k}=""')
                args_new.append(f'**kwargs')
            else:
                for r in args_reduced:
                    if "returnedTags" in r:
                        args_new.append(f"returnedTags={tags['returnedTags']}")
                    # make 'skip' and 'first' optional by setting them to None (return all values)
                    # this still offers the possibility to overwrite them
                    elif r=="skip":
                        args_new.append(f'{r}=None')
                    elif r=="first":
                        args_new.append(f'{r}=None')
                    else:
                        args_new.append(f'{r}=""')
            custom_args = ', '.join(args_new)
            
            #'write' the method to the file
            print(f"    def {i}(self, {custom_args}):", file=f)
            # 'write' docstring
            print('        """', file=f)
            for p in param:
                print(f"{p}", file=f)
            print('        """', file=f)
            print("        try:", file=f)
            # 'write' AXL call
            # special treatment for 'getNumDevices' - nothing to unpack in the result
            if i.startswith("getNumDevices"):
                print(f'            return self.client.{i}(deviceclass)["return"]', file=f)
            # special treatment for 'getOSVersion' - dict key called 'os' instead of 'oSVersion'
            elif i.startswith("getOSVersion"):
                print(f'            return self.client.{i}({", ".join(axl_args)})["return"]["os"]', file=f)
            # special treatment for 'getCCMVersion' - nothing to unpack in the result
            elif i.startswith("getCCMVersion"):
                print(f'            return self.client.{i}(**kwargs)["return"]', file=f)
            # special treatment for 'listChange' - only working with the startChangeId argument
            elif i.startswith("listChange"):
                print(f'            return self.client.{i}(startChangeId=startChangeId)', file=f)
            # unpack result of 'list' operations. Capture empty results.
            elif i.startswith("list"):
                print(f'            returnvalue = self.client.{i}({", ".join(axl_args)})', file=f)
                print(f'            return returnvalue["return"]["{element}"] if returnvalue["return"] else None', file=f)
            # unpack result of 'get' operations
            elif i.startswith("get"):
                print(f'            return self.client.{i}(**kwargs)["return"]["{element}"]', file=f)
            # for 'add' operations the arguments need to be send as dictionary
            elif i.startswith("add"):
                print(f'            return self.client.{i}('+'{'+f'{", ".join(axl_args)}'+'}'+f')["return"]', file=f)
            elif i.startswith("update"):
                if axl_args:
                    print(f'            return self.client.{i}({", ".join(axl_args)}, **kwargs)["return"]', file=f)
                else:
                    print(f'            return self.client.{i}(**kwargs)["return"]', file=f)
            elif i.startswith("executeSQLQuery"):
                print(f'            query_result = self.client.{i}({", ".join(axl_args)})["return"]', file=f)
                print('            return [{element.tag: element.text for element in row} for row in query_result["row"]] if query_result else []', file=f)
            else:
                print(f'            return self.client.{i}({", ".join(axl_args)})["return"]', file=f)
            print("        except Fault as e:", file=f)
            print("            return e", file=f)
            print("", file=f)


if __name__ == "__main__":
    main()
