const eventSource = new EventSource("/api/v1/stream/system-design?tech_stack=Python&topic=秒杀系统");

eventSource.onmessage = function(event) {
    if (event.data === "[DONE]") {
        eventSource.close();
        return;
    }
    // 把 content 追加到页面上
    const content = event.data;
    document.getElementById("answer-box").innerText += content;
};