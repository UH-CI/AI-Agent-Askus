import React from "react";

const ChatLoading = () => {
    // Loading animation for chatbot
    return (
        <div className="d-flex py-1">
            <span className="dot delay-1"/>
            <span className="dot delay-2"/>
            <span className="dot delay-3"/>
        </div>
    );
}

export default ChatLoading;