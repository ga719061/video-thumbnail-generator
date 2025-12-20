import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOST = '192.168.0.149'
USER = 'ga719061'
PWD = 'Qwe22488329!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=22, username=USER, password=PWD, timeout=10)

sftp = ssh.open_sftp()

test_file = '/God/test_write.txt'
print(f"Attempting to write to: {test_file}")

try:
    with sftp.file(test_file, 'wb') as f:
        f.write(f"Test write at {time.ctime()}".encode())
    print("Write successful!")
    
    stat = sftp.stat(test_file)
    print(f"Test file stat: {stat}")
    
    # Clean up
    sftp.remove(test_file)
    print("Test file removed.")
except Exception as e:
    print(f"Write FAILED: {e}")

# Now check the real thumbnail path again
thumbnail_path = '/God/Hantai Anime/LIVE 2D/@eaDir/Ahri PornStar - MF [cinematic].mp4/SYNOVIDEO_VIDEO_SCREENSHOT.jpg'
print(f"\nRe-checking thumbnail: {thumbnail_path}")
try:
    stat = sftp.stat(thumbnail_path)
    print(f"Current stat: {stat}")
except Exception as e:
    print(f"Stat error: {e}")

sftp.close()
ssh.close()
