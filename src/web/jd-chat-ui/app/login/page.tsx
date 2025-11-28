"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const endpoint = isLogin ? "/api/v1/login" : "/api/v1/register";
    // 你的后端地址
    const API_URL = "http://127.0.0.1:8000" + endpoint;

    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (res.ok) {
      if (isLogin) {
        const data = await res.json();
        // 保存 Token 到 localStorage
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("username", username);
        router.push("/"); // 跳转回主页
      } else {
        alert("注册成功，请登录");
        setIsLogin(true);
      }
    } else {
      alert("操作失败：" + res.statusText);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md bg-white p-8 rounded-xl shadow-md">
        <h2 className="text-2xl font-bold mb-6 text-center">{isLogin ? "登录 JD Agent" : "注册新账号"}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            className="w-full p-3 border rounded-lg"
            placeholder="用户名"
            value={username} onChange={e => setUsername(e.target.value)}
          />
          <input
            className="w-full p-3 border rounded-lg"
            type="password"
            placeholder="密码"
            value={password} onChange={e => setPassword(e.target.value)}
          />
          <button className="w-full bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700">
            {isLogin ? "登录" : "注册"}
          </button>
        </form>
        <div className="mt-4 text-center text-sm text-blue-600 cursor-pointer" onClick={() => setIsLogin(!isLogin)}>
          {isLogin ? "没有账号？去注册" : "已有账号？去登录"}
        </div>
      </div>
    </div>
  );
}