"""
Fix for pandas_ta compatibility with newer numpy versions.
"""

import os
import sys

# Path to the pandas_ta squeeze_pro.py file
file_path = os.path.join(sys.prefix, 'Lib', 'site-packages', 'pandas_ta', 'momentum', 'squeeze_pro.py')
if not os.path.exists(file_path):
    # Try user site-packages
    import site
    user_site = site.getusersitepackages()
    file_path = os.path.join(user_site, 'pandas_ta', 'momentum', 'squeeze_pro.py')

if os.path.exists(file_path):
    print(f"Found file at: {file_path}")
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace 'NaN' with 'nan'
    if 'from numpy import NaN as npNaN' in content:
        content = content.replace('from numpy import NaN as npNaN', 'from numpy import nan as npNaN')
        
        # Write the file back
        with open(file_path, 'w') as f:
            f.write(content)
        
        print("Fixed pandas_ta compatibility issue with numpy.")
    else:
        print("No need to fix, file already compatible.")
else:
    print(f"Could not find file: {file_path}")
    print("Please check the installation path of pandas_ta.")
