import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.149', port=22, username='ga719061', password='Qwe22488329!', timeout=10)

sftp = ssh.open_sftp()

# 檢查特定影片的 @eaDir 資料夾內的所有檔案
video_name = 'Ahri PornStar - MF [cinematic].mp4'
eadir_path = f'/God/Hantai Anime/LIVE 2D/@eaDir/{video_name}'

print(f"Listing all files in: {eadir_path}")

try:
    items = sftp.listdir(eadir_path)
    for item in items:
        try:
            stat = sftp.stat(f"{eadir_path}/{item}")
            print(f"  - {item} ({stat.st_size} bytes, modified: {stat.st_mtime})")
        except:
            print(f"  - {item} (could not get stat)")
except Exception as e:
    print(f"Error listing eadir subfolder: {e}")

sftp.close()
ssh.close()
