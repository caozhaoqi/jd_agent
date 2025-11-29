// 前端调用示例代码
const startMock = async () => {
  const response = await fetch("http://127.0.0.1:8000/api/v1/stream/mock-interview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jd_text: "Python后端开发..." })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split("\n\n");

    lines.forEach(line => {
      if (line.startsWith("data: ")) {
        const jsonStr = line.replace("data: ", "");
        if (jsonStr === "[DONE]") return;

        try {
          const msg = JSON.parse(jsonStr);
          // msg.role 是 'interviewer' 或 'candidate'
          // msg.content 是 内容
          console.log(`[${msg.role}]: ${msg.content}`);
          // 这里调用 setMessages 更新 UI
        } catch (e) {}
      }
    });
  }
};