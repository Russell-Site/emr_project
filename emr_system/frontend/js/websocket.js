// ============================================================
// websocket.js
// Real-time WebSocket connection for the EMR system
// ============================================================

let socket = null;

function connectWebSocket() {

    if (socket && socket.readyState === WebSocket.OPEN) {
        console.log("🔌 WebSocket is already connected.");
        return;
    }

    const protocol =
        window.location.protocol === "https:" ? "wss:" : "ws:";

    const host = window.location.host;

    const wsUrl = `${protocol}//${host}/ws`;

    console.log("🔌 Connecting to WebSocket:", wsUrl);

    socket = new WebSocket(wsUrl);

    // Make it accessible from the browser console
    window.socket = socket;

    socket.onopen = function () {
        console.log("✅ WebSocket connected!");
    };

    socket.onmessage = function (event) {

        console.log("🔥 WebSocket message received:", event.data);

        try {

            const data = JSON.parse(event.data);

            console.log("📨 Parsed WebSocket message:", data);

            handleWebSocketMessage(data);

        } catch (error) {

            console.error(
                "❌ Invalid WebSocket message:",
                error
            );

        }
    };

    socket.onclose = function () {

        console.log("🔌 WebSocket disconnected.");

        socket = null;
        window.socket = null;

        setTimeout(connectWebSocket, 3000);
    };

    socket.onerror = function (error) {

        console.error(
            "❌ WebSocket error:",
            error
        );

    };
}


function handleWebSocketMessage(data) {

    switch (data.type) {

        case "pong":

            console.log(
                "🏓 Server response:",
                data.message
            );

            break;


        case "patient_created":

            console.log(
                "👤 New patient created:",
                data.patient
            );

            if (typeof runSearch === "function") {
    runSearch();
}

            if (typeof showToast === "function") {
                showToast(
                    "👤 A new patient was registered.",
                    "success"
                );
            }

            break;


        case "patient_updated":

            console.log(
                "✏️ Patient updated:",
                data.patient
            );

            if (typeof runSearch === "function") {
    runSearch();
}

            if (typeof showToast === "function") {
                showToast(
                    "✏️ A patient record was updated.",
                    "success"
                );
            }

            break;


        case "patient_deleted":

            console.log(
                "🗑️ Patient archived:",
                data.patient_id
            );

            if (typeof runSearch === "function") {
    runSearch();
}

            if (typeof showToast === "function") {
                showToast(
                    "🗑️ A patient record was archived.",
                    "warning"
                );
            }

            break;


        default:

            console.log(
                "📨 Unknown WebSocket event:",
                data
            );
    }
}


function sendWebSocketMessage(message) {

    if (
        !socket ||
        socket.readyState !== WebSocket.OPEN
    ) {

        console.warn(
            "⚠️ WebSocket is not connected."
        );

        return;
    }

    socket.send(
        JSON.stringify(message)
    );
}


connectWebSocket();