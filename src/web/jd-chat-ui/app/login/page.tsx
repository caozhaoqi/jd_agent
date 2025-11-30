"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, User, Lock, LogIn, UserPlus, AlertCircle, CheckCircle2 } from "lucide-react";
import clsx from "clsx";

export default function LoginPage() {
  const router = useRouter();

  // --- 状态管理 ---
  const [isLogin, setIsLogin] = useState(true); // 切换 登录/注册
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");       // 错误信息
  const [success, setSuccess] = useState("");   // 成功信息 (注册成功用)

  // --- 提交逻辑 ---
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!username || !password) {
        setError("请输入用户名和密码");
        return;
    }

    setIsLoading(true);

    const endpoint = isLogin ? "/api/v1/login" : "/api/v1/register";
    const API_URL = "http://127.0.0.1:8000" + endpoint;

    try {
        const res = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });

        const data = await res.json();

        if (res.ok) {
            if (isLogin) {
                // --- 登录成功 ---
                localStorage.setItem("token", data.access_token);
                localStorage.setItem("username", username);
                router.push("/"); // 跳转主页
            } else {
                // --- 注册成功 ---
                setSuccess("注册成功！请使用新账号登录。");
                setIsLogin(true); // 自动切回登录模式
                setPassword("");  // 清空密码
            }
        } else {
            // --- 后端返回错误 (如用户名已存在) ---
            setError(data.detail || "操作失败，请重试");
        }
    } catch (err) {
        // --- 网络错误 ---
        setError("无法连接到服务器，请检查后端是否启动。");
    } finally {
        setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full bg-white p-8 rounded-2xl shadow-xl border border-gray-100">

        {/* 顶部标题 */}
        <div className="text-center mb-8">
            <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg shadow-blue-200">
                {isLogin ? <LogIn size={24} /> : <UserPlus size={24} />}
            </div>
            <h2 className="text-3xl font-bold text-gray-900">
                {isLogin ? "欢迎回来" : "创建账号"}
            </h2>
            <p className="text-gray-500 text-sm mt-2">
                JD Agent - 您的 AI 面试助手
            </p>
        </div>

        {/* 提示信息区域 */}
        {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg flex items-center gap-2 border border-red-100">
                <AlertCircle size={16} /> {error}
            </div>
        )}
        {success && (
            <div className="mb-4 p-3 bg-green-50 text-green-600 text-sm rounded-lg flex items-center gap-2 border border-green-100">
                <CheckCircle2 size={16} /> {success}
            </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* 用户名 */}
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                <User size={18} />
            </div>
            <input
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
              placeholder="请输入用户名"
              value={username}
              onChange={e => setUsername(e.target.value)}
              disabled={isLoading}
            />
          </div>

          {/* 密码 */}
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                <Lock size={18} />
            </div>
            <input
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
              type="password"
              placeholder="请输入密码"
              value={password}
              onChange={e => setPassword(e.target.value)}
              disabled={isLoading}
            />
          </div>

          {/* 按钮 */}
          <button
            disabled={isLoading}
            className={clsx(
                "w-full py-3 rounded-lg text-white font-medium transition-all shadow-md flex justify-center items-center gap-2",
                isLoading
                    ? "bg-blue-400 cursor-not-allowed"
                    : "bg-blue-600 hover:bg-blue-700 hover:shadow-lg active:scale-[0.98]"
            )}
          >
            {isLoading && <Loader2 className="animate-spin" size={18} />}
            {isLogin ? "登 录" : "注 册"}
          </button>
        </form>

        {/* 底部切换 */}
        <div className="mt-6 text-center text-sm">
          <span className="text-gray-500">
            {isLogin ? "还没有账号？" : "已有账号？"}
          </span>
          <span
            className="text-blue-600 font-semibold cursor-pointer hover:underline ml-1"
            onClick={() => {
                setIsLogin(!isLogin);
                setError("");
                setSuccess("");
            }}
          >
            {isLogin ? "立即注册" : "直接登录"}
          </span>
        </div>

      </div>
    </div>
  );
}