"""Keep the verification browser on one desktop with no minimize button."""
from pathlib import Path
import xml.etree.ElementTree as ET

source = Path("/etc/xdg/openbox/rc.xml")
tree = ET.parse(source)
for path, value in [
    ("./{*}desktops/{*}number", "1"),
    ("./{*}desktops/{*}firstdesk", "1"),
    ("./{*}theme/{*}titleLayout", "NLMC"),
]:
    node = tree.find(path)
    if node is None:
        raise RuntimeError(f"Openbox setting missing: {path}")
    node.text = value
ET.register_namespace("", "http://openbox.org/3.4/rc")
tree.write("/etc/voxpull-openbox.xml", encoding="utf-8", xml_declaration=True)
