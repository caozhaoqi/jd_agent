import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
from dotenv import load_dotenv
import os

def pytest_configure(config):
    """
    在 pytest 测试会话开始前加载环境变量。
    这是一个 pytest 钩子函数，能确保环境变量在所有模块导入前被设置。
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dotenv_path = os.path.join(project_root, '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        print(f"\n✅ Conftest: Loaded environment variables from {dotenv_path}")
    else:
        print(f"\n⚠️ Conftest: .env file not found at {dotenv_path}")

# 注意：此处不再有任何 from app... 的导入

# 创建一个内存数据库用于测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@pytest.fixture(name="session")
def session_fixture():
    """创建一个数据库会话用于测试"""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """创建一个测试客户端，替换依赖项中的数据库会话"""
    # --- 延迟导入 ---
    from app.main import app
    from app.core.db_auth import get_session

    def override_get_session():
        return session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """创建一个测试用户"""
    # --- 延迟导入 ---
    from app.core.db_auth import get_password_hash
    from app.core.models import User

    hashed_password = get_password_hash("test_password")
    user = User(username="test_user", hashed_password=hashed_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="test_session")
def test_session_fixture(session: Session, test_user):
    """创建一个测试会话"""
    # --- 延迟导入 ---
    from app.core.models import ChatSession

    chat_session = ChatSession(title="测试会话", user_id=test_user.id)
    session.add(chat_session)
    session.commit()
    session.refresh(chat_session)
    return chat_session


@pytest.fixture(name="test_token")
def test_token_fixture(test_user, client: TestClient):
    """获取测试用户的访问令牌"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_user", "password": "test_password"},
    )
    data = response.json()
    return data["data"]["access_token"]


@pytest.fixture(scope="session")
def event_loop():
    """为测试提供事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
