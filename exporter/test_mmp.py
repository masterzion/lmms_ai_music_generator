import xml.etree.ElementTree as ET

def create_mmp():
    root = ET.Element('lmms-project', version="1.0", creator="python")
    song = ET.SubElement(root, 'song', type="0")
    
    # Add head
    head = ET.SubElement(root, 'head')
    
    # Add trackcontainers
    song_tc = ET.SubElement(song, 'trackcontainer', type="song", x="5", y="5", width="600", height="300")
    bb_tc = ET.SubElement(song, 'trackcontainer', type="bbtrackcontainer", x="5", y="310", width="600", height="300")
    
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    tree.write("dummy.mmp", encoding="utf-8", xml_declaration=True)

if __name__ == '__main__':
    create_mmp()
