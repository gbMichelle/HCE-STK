from argparse import ArgumentParser


parser = ArgumentParser(description="A patcher to upgrade limits in tool.exe. Works for stock tool and OS_Tool. Does not work with packed tool exes that are compressed. Don't use this on anything but tool")
parser.add_argument('-i', '--enable-vertex-and-index-buffer-upgrade', dest='vertex_index_up', action='store_const',
                    const=True, default=False,
                    help='Upgrades the vertex and index buffer size. Not done by default because of reports of it breaking animation import/compression.')
parser.add_argument('tool_exe', metavar='tool_exe', type=str,
                    help='The tool EXE we want to operate on.')
args = parser.parse_args()
    
import sys
if sys.version_info[0] >= 3 and sys.version_info[1] >= 2:
    with open(args.tool_exe, 'r+b') as f:
    
        print("Patching singeplayer map compilation for multi language support...")
        
        # This fixes an issue where singleplayer and UI maps were compiled
        # with settings that would only make them work for one set of data maps.
        
        f.seek(0x55451)
        f.write((0).to_bytes(1, byteorder='little'))
        
        print("Patching max mapfile size...")
        
        # These changes make it so there is no max size,
        # and that the header never contains anything but 0 as the size.
        
        # MOV size into ebx instead of header.
        f.seek(0x5316B)
        f.write((0x8BD890).to_bytes(3, byteorder='big'))
        
        # MOV size from ebx into eax instead of from header.
        f.seek(0x531BF)
        f.write((0x8BC390).to_bytes(3, byteorder='big'))
        
        # Remove max size fail condition by making a jump unconditional.
        f.seek(0x531D2)
        f.write((0xEB).to_bytes(1, byteorder='big'))
        
        if args.vertex_index_up:
            print("Patching vertex and index buffer size...")
            # Change vertex-index buffer size from 32MB to 96MB.
            # Opensauce overwrites this change, so for now it only works for vanilla maps.
            f.seek(0x54D57)
            f.write((0x06000000).to_bytes(4, byteorder='little'))
            
        print("Done!")
else:
    print("Python Version outdated. Needs to be at least 3.2.")
