import os
workspace_root = "/home/user/workspace"
target_path = "/home/user/workspace-evil/file.txt"
print(target_path.startswith(workspace_root))

target_path_correct = "/home/user/workspace/file.txt"
print(target_path_correct.startswith(workspace_root + os.sep))
