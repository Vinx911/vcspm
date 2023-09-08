#!/usr/bin/env python

import os
import sys

package_name = sys.argv[1]
package_dir = sys.argv[2]

readme = os.path.join(package_dir, "README.txt")

with open(readme, "a", encoding='utf-8') as f:
    f.write("\n这是一条通过脚本输入的文本\n")
