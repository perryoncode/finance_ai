document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("chat-send");
  const input = document.getElementById("chat-input");
  const out = document.getElementById("chat-output");
  const timeframeSelect = document.getElementById("timeframe") || { value: "30" }; // Default to 30 days if not found
  
  if (!btn || !input || !out) return;

  async function send() {
    const message = input.value.trim();
    if (!message) return;
    
    // Show user message
    const userMessageDiv = document.createElement("div");
    userMessageDiv.className = "user-message";
    userMessageDiv.innerHTML = `<strong>You:</strong> ${message}`;
    out.appendChild(userMessageDiv);
    
    // Show typing indicator
    const aiMessageDiv = document.createElement("div");
    aiMessageDiv.className = "ai-message";
    aiMessageDiv.innerHTML = `<strong>Finance AI:</strong> <span class="typing-indicator">Thinking...</span>`;
    out.appendChild(aiMessageDiv);
    
    // Scroll to bottom
    out.scrollTop = out.scrollHeight;
    
    // Clear input
    input.value = "";
    
    try {
      const days = parseInt(timeframeSelect.value) || 30;
      const res = await fetch("/chat/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, days })
      });
      
      if (!res.ok) {
        throw new Error(`Server responded with status: ${res.status}`);
      }
      
      const data = await res.json();
      
      // Replace typing indicator with actual response
      aiMessageDiv.innerHTML = `<strong>Finance AI:</strong> ${data.reply || "I couldn't process your request at this time."}`;
    } catch (error) {
      console.error("Error:", error);
      aiMessageDiv.innerHTML = `<strong>Finance AI:</strong> Sorry, I encountered an error: ${error.message}`;
    }
    
    // Scroll to bottom again
    out.scrollTop = out.scrollHeight;
  }
  
  // Send message on button click
  btn.addEventListener("click", send);
  
  // Send message on Enter key (but allow Shift+Enter for new line)
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });
});
