import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.149', port=22, username='ga719061', password='Qwe22488329!', timeout=10)

sftp = ssh.open_sftp()

# 檢查特定影片的縮圖
video_name = 'Ahri PornStar - MF [cinematic].mp4'
eadir_path = f'/God/Hantai Anime/LIVE 2D/@eaDir/{video_name}'
thumbnail_path = f'{eadir_path}/SYNOVIDEO_VIDEO_SCREENSHOT.jpg'

print(f"Checking: {thumbnail_path}")

try:
    stat = sftp.stat(thumbnail_path)
    print(f"FOUND! Size: {stat.st_size} bytes")
except Exception as e:
    print(f"NOT FOUND: {e}")

# 檢查 @eaDir 是否存在
print(f"\nChecking @eaDir folder:")
try:
    items = sftp.listdir('/God/Hantai Anime/LIVE 2D/@eaDir')
    print(f"@eaDir has {len(items)} items")
    for item in items[:5]:
        print(f"  - {item}")
except Exception as e:
    print(f"@eaDir error: {e}")

sftp.close()
ssh.close()
