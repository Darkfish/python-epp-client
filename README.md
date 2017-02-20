# python-epp-client
Minimalist script for manually executing EPP commands with client-certificate auth

## Usage

```
$ python eppclient.py --server nzrsepp.vagrant.dev --certificate crt.pem --private-key key.pem login.xml info.xml 
2017-02-21 10:37:54,475 INFO  - Making SSL connection to nzrsepp.vagrant.dev:700
2017-02-21 10:37:54,544 INFO Trying to read EPP Greeting from server
2017-02-21 10:37:54,544 INFO   - Trying to read 4-byte header from socket
2017-02-21 10:37:54,625 INFO   - Found length header, trying to read 584 bytes
2017-02-21 10:37:54,627 INFO <?xml version="1.0" encoding="UTF-8"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><greeting><svID>nzrsepp.vagrant.dev</svID><svDate>2017-02-20T21:38:19+00:00</svDate><svcMenu><version>1.0</version><lang>en</lang><objURI>urn:ietf:params:xml:ns:domain-1.0</objURI><objURI>urn:ietf:params:xml:ns:contact-1.0</objURI><svcExtension><extURI>urn:ietf:params:xml:ns:secDNS-1.1</extURI></svcExtension></svcMenu><dcp><access><personalAndOther/></access><statement><purpose><admin/><prov/></purpose><recipient><ours/></recipient><retention><business/></retention></statement></dcp></greeting></epp>

2017-02-21 10:37:54,627 INFO Sending login.xml
2017-02-21 10:37:54,627 INFO Sending XML (556 bytes):
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
  <command>
    <login>
      <clID>999</clID>
      <pw>asdfasdf</pw>
      <options>
        <version>1.0</version>
        <lang>en</lang>
      </options>
      <svcs>
        <objURI>urn:ietf:params:xml:ns:domain-1.0</objURI>
        <objURI>urn:ietf:params:xml:ns:contact-1.0</objURI>
        <svcExtension>
          <extURI>urn:ietf:params:xml:ns:secDNS-1.1</extURI>
        </svcExtension>
      </svcs>
    </login>
  </command>
</epp>

2017-02-21 10:37:55,630 INFO   - Trying to read 4-byte header from socket
2017-02-21 10:37:55,630 INFO   - Found length header, trying to read 238 bytes
2017-02-21 10:37:55,630 INFO Response from server: 
<?xml version="1.0" encoding="UTF-8"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response><result code="1000"><msg lang="en">Command completed successfully</msg></result><trID><svTRID>7,1323159525[1]+2</svTRID></trID></response></epp>

2017-02-21 10:41:06,474 INFO Sending check.xml
2017-02-21 10:41:06,474 INFO Sending XML (286 bytes):
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
  <command>
    <check>
      <domain:check xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">
        <domain:name>nzrs.net.nz</domain:name>
      </domain:check>
    </check>
    <clTRID>check-domain-0123</clTRID>
  </command>
</epp>

2017-02-21 10:41:07,475 INFO   - Trying to read 4-byte header from socket
2017-02-21 10:41:07,476 INFO   - Found length header, trying to read 439 bytes
2017-02-21 10:41:07,476 INFO Response from server: 
<?xml version="1.0" encoding="UTF-8"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response><result code="1000"><msg lang="en">Command completed successfully</msg></result><resData><domain:chkData xmlns:domain="urn:ietf:params:xml:ns:domain-1.0"><domain:cd><domain:name avail="0">nzrs.net.nz</domain:name></domain:cd></domain:chkData></resData><trID><clTRID>check-domain-0123</clTRID><svTRID>7,1323159583</svTRID></trID></response></epp>
```
