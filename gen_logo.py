import subprocess
try:
    result = subprocess.run(['figlet', '-f', 'ansi_shadow', 'Aura'], capture_output=True, text=True)
    if result.returncode == 0:
        print("ANSI_SHADOW:")
        print(result.stdout)
    result = subprocess.run(['figlet', '-f', 'ansishadow', 'AURA'], capture_output=True, text=True)
    if result.returncode == 0:
        print("ANSISHADOW AURA:")
        print(result.stdout)
except FileNotFoundError:
    print("figlet not installed")
