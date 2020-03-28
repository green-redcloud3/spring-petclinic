import os
import lxml.etree as ET
print(os.environ['WORKSPACE'])


# dom = ET.parse("%s/zap_scan_dev.xml" % os.environ['WORKSPACE'])
# xslt = ET.parse("%s/zap_scan_dev.xsl" % os.environ['WORKSPACE'])

dom = ET.parse("zap_scan_dev.xml")
xslt = ET.parse("zap_scan_dev.xsl")


transform = ET.XSLT(xslt)
newdom = transform(dom)
# print(ET.tostring(newdom, pretty_print=True))
# file = open("%s/zap_scan_dev.html" % os.environ['WORKSPACE'],"w") 
file = open("zap_scan_dev.html" ,"w") 
file.write(ET.tostring(newdom, pretty_print=True))
file.close()
