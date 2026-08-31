# Usage: copy_file.py SRC_FILE DEST_FILE

import shutil
import sys

shutil.copy(sys.argv[1], sys.argv[2])
