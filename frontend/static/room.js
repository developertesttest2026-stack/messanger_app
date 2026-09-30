const API_BASE = window.location.origin;

const roomId = new URLSearchParams(window.location.search).get("id");

function getToken() {
    return localStorage.getItem("access_token");
}

async function fetchWithAuth(url, options = {}) {
    const token = getToken();
    return fetch(url, {
        ...options,
        headers: {
            ...(options.headers || {}),
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json",
        },
    });
}

async function loadRoomDetails() {
    const res = await fetchWithAuth(`${API_BASE}/rooms/${roomId}`);
    const room = await res.json();
    document.getElementById("roomTitle").textContent = room.name;
}

async function loadMessages() {
    const res = await fetchWithAuth(`${API_BASE}/rooms/${roomId}/messages`);
    const messages = await res.json();
    const container = document.getElementById("roomMessages");
    container.innerHTML = "";

    messages.forEach(msg => {
        const el = document.createElement("div");
        el.className = "message";
        el.textContent = `${msg.user_id}: ${msg.text}`;
        container.appendChild(el);
    });
}

async function sendMessage(e) {
    e.preventDefault();
    const input = document.getElementById("messageInput");
    const text = input.value.trim();

    if (!text) return;

    await fetchWithAuth(`${API_BASE}/rooms/${roomId}/messages`, {
        method: "POST",
        body: JSON.stringify({ text }),
    });

    input.value = "";
    await loadMessages();
}

window.addEventListener("DOMContentLoaded", async () => {
    if (!roomId) {
        window.location.href = "/dashboard";
        return;
    }

    await loadRoomDetails();
    await loadMessages();

    document.getElementById("roomMessageForm").addEventListener("submit", sendMessage);
});



const clientId = crypto.randomUUID();
let lastPresenceEventId = 0;
let receivedInitialActivity = false;

async function sendPresenceHeartbeat() {
    await fetchWithAuth(`${API_BASE}/rooms/${roomId}/presence`, {
        method: "POST",
        body: JSON.stringify({ client_id: clientId }),
    });
}

async function pollRoomActivity() {
    try {
        const response = await fetchWithAuth(
            `${API_BASE}/rooms/${roomId}/activity?after_id=${lastPresenceEventId}`
        );
        if (!response.ok) return;

        const data = await response.json();
        renderActiveUsers(data.active_users);

        for (const event of data.events) {
            lastPresenceEventId = Math.max(lastPresenceEventId, event.id);

            if (receivedInitialActivity) {
                appendPresenceNotice(event);
            }
        }

        receivedInitialActivity = true;
    } finally {
        window.setTimeout(pollRoomActivity, 3000);
    }
}

function renderActiveUsers(users) {
    const list = document.getElementById("activeUsers");
    list.replaceChildren();

    for (const user of users) {
        const item = document.createElement("li");
        const name = user.full_name || `Пользователь ${user.user_id}`;
        item.textContent = user.username
            ? `${name} (@${user.username})`
            : name;
        list.appendChild(item);
    }
}

function appendPresenceNotice(event) {
    const messages = document.getElementById("roomMessages");
    const item = document.createElement("div");
    item.className = "message system-message";

    const name = event.full_name || `Пользователь ${event.user_id}`;
    item.textContent = event.type === "user_joined"
        ? `${name} присоединился к комнате`
        : `${name} покинул комнату`;

    messages.appendChild(item);
}


await sendPresenceHeartbeat();
await pollRoomActivity();

window.setInterval(() => {
    sendPresenceHeartbeat().catch(console.error);
}, 10000);


window.addEventListener("pagehide", () => {
    fetchWithAuth(
        `${API_BASE}/rooms/${roomId}/presence/${clientId}`,
        { method: "DELETE", keepalive: true }
    ).catch(() => {});
});