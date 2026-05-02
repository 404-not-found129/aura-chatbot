import os
file_path = "/etc/passwd"
print(os.path.abspath(file_path))

file_path2 = "../../etc/passwd"
print(os.path.abspath(file_path2))
