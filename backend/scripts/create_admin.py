"""One-time, interactive bootstrap. Never accept passwords via command arguments."""

from getpass import getpass

from pydantic import ValidationError

from app.api.auth_dependencies import get_auth_store
from app.repositories.auth_store import AuthError
from app.schemas.auth import UserCreate


def main():
    store = get_auth_store()
    if store.list_users(1, 0)["total"]:
        print("Đã có tài khoản. Hãy đăng nhập và dùng trang quản trị.")
        return
    try:
        email = input("Email Admin: ").strip()
        name = input("Tên hiển thị: ").strip()
        password = getpass("Mật khẩu (15–128 ký tự; không hiển thị): ")
        if password != getpass("Nhập lại mật khẩu: "):
            print("Mật khẩu không khớp. Chưa tạo tài khoản.")
            return
        payload = UserCreate(email=email, name=name, password=password, role="ADMIN")
        data = payload.model_dump(exclude={"password"})
        data["password"] = payload.password.get_secret_value()
        store.create_user(data, bootstrap=True)
        print("Đã tạo Admin. Bạn có thể đăng nhập tại http://127.0.0.1:5173.")
    except ValidationError:
        print(
            "Email/tên không hợp lệ hoặc mật khẩu chưa đủ 15–128 ký tự. Chưa tạo tài khoản."
        )
    except AuthError as error:
        print(error.detail)
    except (EOFError, KeyboardInterrupt):
        print("\nĐã hủy. Chưa tạo tài khoản.")


if __name__ == "__main__":
    main()
