document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const apiKeyInput = document.getElementById("apiKeyInput");
    const saveKeyBtn = document.getElementById("saveKeyBtn");
    const keyStatus = document.getElementById("keyStatus");
    const statusLabel = keyStatus.querySelector(".status-label");
    
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    const uploadProgressContainer = document.getElementById("uploadProgressContainer");
    const uploadProgressBar = document.getElementById("uploadProgressBar");
    const uploadProgressText = document.getElementById("uploadProgressText");
    
    const documentList = document.getElementById("documentList");
    const clearDbBtn = document.getElementById("clearDbBtn");
    
    const messagesContainer = document.getElementById("messagesContainer");
    const chatInput = document.getElementById("chatInput");
    const sendBtn = document.getElementById("sendBtn");
    const suggestionsRow = document.getElementById("suggestionsRow");
    
    const citationsPanel = document.getElementById("citationsPanel");
    const closeCitationsBtn = document.getElementById("closeCitationsBtn");
    const citationsContent = document.getElementById("citationsContent");

    // App State
    let apiKey = localStorage.getItem("NVIDIA_API_KEY") || "";
    let activeCitations = [];

    // Initialize Page
    if (apiKey) {
        apiKeyInput.value = apiKey;
        syncApiKey(apiKey);
    } else {
        checkServerKeyStatus();
    }
    refreshDocuments();

    // Textarea auto-resize logic
    chatInput.addEventListener("input", () => {
        chatInput.style.height = "auto";
        chatInput.style.height = (chatInput.scrollHeight) + "px";
        toggleSendButton();
    });

    function toggleSendButton() {
        sendBtn.disabled = !chatInput.value.trim();
    }

    // Suggestions Tags
    document.querySelectorAll(".suggestion-tag").forEach(tag => {
        tag.addEventListener("click", () => {
            chatInput.value = tag.getAttribute("data-query");
            chatInput.focus();
            chatInput.style.height = "auto";
            chatInput.style.height = (chatInput.scrollHeight) + "px";
            toggleSendButton();
        });
    });

    // Save API Key
    saveKeyBtn.addEventListener("click", () => {
        const key = apiKeyInput.value.trim();
        if (!key) {
            alert("Please enter a key.");
            return;
        }
        syncApiKey(key);
    });

    async function syncApiKey(key) {
        try {
            const res = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ api_key: key })
            });
            const data = await res.json();
            if (res.ok) {
                apiKey = key;
                localStorage.setItem("NVIDIA_API_KEY", key);
                keyStatus.className = "key-status-badge status-configured";
                statusLabel.textContent = "API Key Active";
                apiKeyInput.style.borderColor = "rgba(255, 255, 255, 0.05)";
            } else {
                alert(data.detail || "Invalid Key");
            }
        } catch (err) {
            console.error(err);
            alert("Failed to save credentials.");
        }
    }

    async function checkServerKeyStatus() {
        try {
            const res = await fetch("/api/config/status");
            const data = await res.json();
            if (data.has_key) {
                keyStatus.className = "key-status-badge status-configured";
                statusLabel.textContent = "API Key Active (Server)";
            } else {
                keyStatus.className = "key-status-badge status-missing";
                statusLabel.textContent = "No API Key Set";
            }
        } catch (err) {
            console.error("Failed to fetch key status:", err);
        }
    }

    // Ingestion File Uploader
    dropZone.addEventListener("click", () => fileInput.click());
    
    fileInput.addEventListener("change", (e) => {
        const files = Array.from(e.target.files);
        if (files.length > 0) handleUpload(files);
    });

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        const files = Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith(".pdf"));
        if (files.length > 0) handleUpload(files);
    });

    async function handleUpload(files) {
        uploadProgressContainer.classList.remove("hidden");
        uploadProgressBar.style.width = "10%";
        uploadProgressText.textContent = "Preparing files...";

        const formData = new FormData();
        files.forEach(file => formData.append("files", file));
        if (apiKey) {
            formData.append("api_key", apiKey);
        }

        try {
            uploadProgressBar.style.width = "40%";
            uploadProgressText.textContent = "Uploading & parsing PDF...";
            
            const res = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });

            uploadProgressBar.style.width = "80%";
            uploadProgressText.textContent = "Computing vector embeddings...";
            
            const data = await res.json();
            
            if (res.ok) {
                uploadProgressBar.style.width = "100%";
                uploadProgressText.textContent = "Success! Document indexed.";
                setTimeout(() => {
                    uploadProgressContainer.classList.add("hidden");
                }, 3000);
                refreshDocuments();
                checkServerKeyStatus();
            } else {
                throw new Error(data.detail || "Indexing failed");
            }
        } catch (err) {
            console.error(err);
            uploadProgressBar.style.width = "0%";
            uploadProgressText.textContent = `Error: ${err.message}`;
            setTimeout(() => {
                uploadProgressContainer.classList.add("hidden");
            }, 5000);
        }
    }

    // Refresh Sidebar Document List
    async function refreshDocuments() {
        try {
            const res = await fetch("/api/documents");
            const data = await res.json();
            documentList.innerHTML = "";
            
            if (!data.documents || data.documents.length === 0) {
                documentList.innerHTML = `
                    <div class="empty-state-list">
                        <p>No documents indexed yet.</p>
                    </div>
                `;
                return;
            }

            data.documents.forEach(doc => {
                const docCard = document.createElement("div");
                docCard.className = "doc-item";
                docCard.innerHTML = `
                    <div class="doc-info">
                        <i class="fa-solid fa-file-pdf"></i>
                        <span class="doc-name" title="${doc.filename}">${doc.filename}</span>
                    </div>
                    <span class="doc-chunks">${doc.chunks} pg-chunks</span>
                `;
                documentList.appendChild(docCard);
            });
        } catch (err) {
            console.error(err);
        }
    }

    // Clear DB
    clearDbBtn.addEventListener("click", async () => {
        if (!confirm("Are you sure you want to delete all indexed documents from the vector store?")) return;
        try {
            const res = await fetch("/api/clear", { method: "POST" });
            if (res.ok) {
                refreshDocuments();
                activeCitations = [];
                citationsPanel.classList.add("hidden");
                appendSystemMessage("Vector database cleared. Please upload new files.");
            }
        } catch (err) {
            console.error(err);
        }
    });

    // Appending simple messages
    function appendSystemMessage(text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "message system-message";
        msgDiv.innerHTML = `
            <div class="avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="message-content-wrapper">
                <div class="sender-name">System</div>
                <div class="message-bubble"><p>${text}</p></div>
            </div>
        `;
        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Chat Sending
    sendBtn.addEventListener("click", () => handleSendQuery());
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendQuery();
        }
    });

    async function handleSendQuery() {
        const query = chatInput.value.trim();
        if (!query) return;

        // Reset Input
        chatInput.value = "";
        chatInput.style.height = "auto";
        toggleSendButton();

        // 1. Render User Message
        const userMsgDiv = document.createElement("div");
        userMsgDiv.className = "message user-message";
        userMsgDiv.innerHTML = `
            <div class="avatar"><i class="fa-solid fa-user"></i></div>
            <div class="message-content-wrapper">
                <div class="sender-name">You</div>
                <div class="message-bubble"><p>${escapeHtml(query)}</p></div>
            </div>
        `;
        messagesContainer.appendChild(userMsgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // 2. Render typing indicator placeholder
        const assistantMsgDiv = document.createElement("div");
        assistantMsgDiv.className = "message system-message";
        assistantMsgDiv.innerHTML = `
            <div class="avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="message-content-wrapper">
                <div class="sender-name">Nemotron Assistant</div>
                <div class="message-bubble">
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        messagesContainer.appendChild(assistantMsgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        const bubbleContent = assistantMsgDiv.querySelector(".message-bubble");

        // 3. Request Streaming API
        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query: query,
                    api_key: apiKey
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Generation failed.");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            let assistantText = "";
            let streamStarted = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunkStr = decoder.decode(value);
                const lines = chunkStr.split("\n\n");
                
                for (const line of lines) {
                    if (line.startsWith("citations:")) {
                        activeCitations = JSON.parse(line.substring(10));
                        renderCitationsPanel(activeCitations);
                    } else if (line.startsWith("text:")) {
                        if (!streamStarted) {
                            // Clear typing indicator on first token
                            bubbleContent.innerHTML = "";
                            streamStarted = true;
                        }
                        assistantText += line.substring(5);
                        bubbleContent.innerHTML = renderMarkdown(assistantText);
                    } else if (line.startsWith("error:")) {
                        throw new Error(line.substring(6));
                    }
                }
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }

            // Hook citation click listeners once stream ends
            setupCitationListeners();

        } catch (err) {
            console.error(err);
            bubbleContent.innerHTML = `<p class="status-missing" style="background:none; border:none; padding:0;"><i class="fa-solid fa-triangle-exclamation"></i> Error: ${err.message}</p>`;
        }
    }

    // Helper: Escape HTML
    function escapeHtml(unsafe) {
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }

    // Render basic markdown, bolding, lists, and replace [X] citation marks
    function renderMarkdown(text) {
        // Render block code
        let html = text.replace(/```([\s\S]*?)```/g, (match, code) => {
            return `<pre><code>${escapeHtml(code.trim())}</code></pre>`;
        });
        
        // Render inline code
        html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
        
        // Render bolding
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        
        // Convert citation markers e.g. [1] or [2] into interactive link circles
        html = html.replace(/\[(\d+)\]/g, (match, id) => {
            return `<span class="citation-link" data-citation-id="${id}">${id}</span>`;
        });
        
        // Split by lines and wrap in paragraphs
        const lines = html.split("\n");
        let formattedLines = [];
        let inList = false;
        
        for (let line of lines) {
            line = line.trim();
            if (!line) continue;
            
            if (line.startsWith("- ") || line.startsWith("* ")) {
                if (!inList) {
                    formattedLines.push("<ul>");
                    inList = true;
                }
                formattedLines.push(`<li>${line.substring(2)}</li>`);
            } else {
                if (inList) {
                    formattedLines.push("</ul>");
                    inList = false;
                }
                if (!line.startsWith("<pre>")) {
                    formattedLines.push(`<p>${line}</p>`);
                } else {
                    formattedLines.push(line);
                }
            }
        }
        if (inList) formattedLines.push("</ul>");
        
        return formattedLines.join("");
    }

    // Render Citations panel contents
    function renderCitationsPanel(citations) {
        citationsContent.innerHTML = "";
        if (!citations || citations.length === 0) {
            citationsContent.innerHTML = `<p class="empty-state-list">No sources retrieved.</p>`;
            return;
        }

        citations.forEach(cit => {
            const card = document.createElement("div");
            card.className = "citation-card";
            card.id = `cit-card-${cit.id}`;
            card.innerHTML = `
                <div class="citation-meta">
                    <span class="citation-num">${cit.id}</span>
                    <span>${cit.source} (Page ${cit.page})</span>
                </div>
                <div class="citation-text">"${escapeHtml(cit.text)}"</div>
            `;
            citationsContent.appendChild(card);
        });
    }

    // Setup Citation link click listeners
    function setupCitationListeners() {
        document.querySelectorAll(".citation-link").forEach(link => {
            link.addEventListener("click", (e) => {
                const citationId = e.target.getAttribute("data-citation-id");
                openCitationCard(citationId);
            });
        });
    }

    function openCitationCard(id) {
        citationsPanel.classList.remove("hidden");
        
        // Remove active highlights
        document.querySelectorAll(".citation-card").forEach(c => c.classList.remove("highlighted"));
        
        const card = document.getElementById(`cit-card-${id}`);
        if (card) {
            card.classList.add("highlighted");
            card.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
    }

    closeCitationsBtn.addEventListener("click", () => {
        citationsPanel.classList.add("hidden");
    });
});
