import bcrypt
from sqlmodel import SQLModel, create_engine, Session, select
from src.app.core.models import User

# 创建数据库连接
sqlite_file_name = "/Users/caozhaoqi/PycharmProjects/JD_agent/src/app/database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)

# 生成密码哈希
password = 'test'.encode('utf-8')
hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
hashed_password_str = hashed_password.decode('utf-8')
print(f"Generated hash: {hashed_password_str}")

# 更新用户密码
with Session(engine) as session:
    user = session.exec(select(User).where(User.username == 'test')).first()
    if user:
        user.hashed_password = hashed_password_str
        session.commit()
        print("User password updated successfully")
    else:
        print("User not found")
