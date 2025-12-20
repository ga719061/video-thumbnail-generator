import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOST = '192.168.0.149'
USER = 'ga719061'
PWD = 'Qwe22488329!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=22, username=USER, password=PWD, timeout=10)

sftp = ssh.open_sftp()

# 特定影片路徑
folder_path = '/God/A/VR'
video_name = 'JohnTron VR_Cherry_Thai Tinder Date Loves Shoot Porn On First Date_2880p_LR_180.mp4'
eadir_path = f'{folder_path}/@eaDir/{video_name}'

print(f"--- Diagnostic for: {video_name} ---")

# 1. 檢查影片本身是否存在
print(f"\n1. Checking video file: {folder_path}/{video_name}")
try:
    stat = sftp.stat(f"{folder_path}/{video_name}")
    print(f"   FOUND! Size: {stat.st_size} bytes")
except:
    print("   VIDEO NOT FOUND!")

# 2. 檢查 @eaDir 資料夾
print(f"\n2. Checking @eaDir: {eadir_path}")
try:
    items = sftp.listdir(eadir_path)
    print(f"   @eaDir exists with {len(items)} items:")
    for item in items:
        try:
            istat = sftp.stat(f"{eadir_path}/{item}")
            print(f"     - {item} ({istat.st_size} bytes, modified: {istat.st_mtime})")
        except:
            print(f"     - {item} (stat failed)")
except Exception as e:
    print(f"   @eaDir folder error: {e}")

# 3. 檢查父目錄權限
print(f"\n3. Checking parent folder permissions: {folder_path}/@eaDir")
try:
    pstat = sftp.stat(f"{folder_path}/@eaDir")
    print(f"   Parent @eaDir permissions: {oct(pstat.st_mode)}")
except Exception as e:
    print(f"   Parent @eaDir error: {e}")

sftp.close()
ssh.close()
