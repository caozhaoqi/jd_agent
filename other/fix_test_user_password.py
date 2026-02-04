import bcrypt

# 生成密码 'test' 的哈希值
password = 'test'.encode('utf-8')
# 使用与应用相同的参数生成哈希
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(password, salt)
print(f"Password hash for 'test': {hashed.decode('utf-8')}")
